import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
#
# plt.switch_backend('MacOSX')
import sklearn as skl
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import seaborn as sns
import copy
import pickle
import json

sns.set()


def getObjects(objectType, date):
    # rating, coords, subratings, name
    pass


def getHoliday(date):
    isHoliday = 0
    if pd.to_datetime('2019-04-15') <= date <= pd.to_datetime('2019-04-27'):
        isHoliday = 1
    elif date == pd.to_datetime('2019-05-01'):
        isHoliday = 1
    elif pd.to_datetime('2019-05-30') <= date <= pd.to_datetime('2019-06-02'):
        isHoliday = 1
    elif date == pd.to_datetime('2019-06-10'):
        isHoliday = 1
    elif pd.to_datetime('2019-06-29') <= date <= pd.to_datetime('2019-08-10'):
        isHoliday = 1
    elif pd.to_datetime('2019-09-28') <= date <= pd.to_datetime('2019-10-212'):
        isHoliday = 1
    return isHoliday


def getCoordinates(uniqueIds, mappings):
    coords = mappings.loc[uniqueIds, 'coordinates']
    return coords


def loadMapping():
    originalData = pd.read_csv('../data/2019-09-27-basel-collections.csv', delimiter=',')
    # keepData = originalData[['geometry', 'coordinates']]
    # drop na osm_id
    cleanIndex = originalData['osm_id'].dropna().index
    keepData = originalData.loc[cleanIndex, ['geometry', 'coordinates', 'osm_id', 'cci_id']]
    keepData.loc[:, 'uniqueId'] = keepData['osm_id'].apply(lambda x: str(int(x))) + "-" + keepData['cci_id'].apply(
        lambda x: str(x))

    keepData.set_index('uniqueId', inplace=True)
    keepData.drop(columns=['osm_id', 'cci_id'], inplace=True)

    # calculate long lat of midpoint
    keepData.loc[:, 'midpoints'] = keepData['coordinates'].apply(lambda x: getMidPoint(x))
    keepData.loc[:, 'long'] = keepData.loc[:, 'midpoints'].apply(lambda x: x[0])
    # keepData.loc[:, 'long'] = skl.preprocessing.scale(keepData['long'])
    keepData.loc[:, 'lat'] = keepData.loc[:, 'midpoints'].apply(lambda x: x[1])
    # keepData.loc[:, 'lat'] = skl.preprocessing.scale(keepData['lat'])
    keepData.drop(columns=['midpoints'], inplace=True)
    return keepData


def addWeatherData(rawData):
    # load weather
    weather = pd.read_csv('../data/weather_symbol.csv', delimiter=';')
    weather.loc[:, 'date'] = weather.iloc[:, 0].apply(lambda x: str(pd.to_datetime(x).date().strftime('%Y-%m-%d')))
    weather.loc[:, 'weatherClass'] = weather.iloc[:, 1]
    weather.loc[:, 'weatherCat'] = weather.iloc[:, 1].apply(lambda x: deriveWeatherCat(x))
    weather.drop(columns=['validdate', 'weather_symbol_1h:idx'], inplace=True)
    weather.set_index('date', inplace=True)

    # map weather to obs
    rawData.loc[:, 'weatherCat'] = "nix"
    dateStringSeries = rawData['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    for k, v in weather['weatherCat'].iteritems():
        rawData.loc[dateStringSeries == k, 'weatherCat'] = v
    return rawData


def getWeatherForDate(date):
    weather = pd.read_csv('../data/weather_symbol.csv', delimiter=';')
    weather.loc[:, 'date'] = weather.iloc[:, 0].apply(lambda x: str(pd.to_datetime(x).date().strftime('%Y-%m-%d')))
    weather.loc[:, 'weatherClass'] = weather.iloc[:, 1]
    weather.loc[:, 'weatherCat'] = weather.iloc[:, 1].apply(lambda x: deriveWeatherCat(x))
    weather.drop(columns=['validdate', 'weather_symbol_1h:idx'], inplace=True)
    weather.set_index('date', inplace=True)
    return weather.loc[date, 'weatherCat']


def addCoordinates(rawData):
    mappings = loadMapping()
    rawData.set_index('uniqueId', inplace=True)
    rawData.loc[:, 'long'] = mappings['long']
    rawData.loc[:, 'lat'] = mappings['lat']

    # rawData.loc[:, 'coordinates'] = mappings['coordinates'].apply(lambda x: getMidPoint(x))
    # rawData.loc[:, 'long'] = rawData.loc[:, 'coordinates'].apply(lambda x: x[0])
    # rawData.loc[:, 'long'] = skl.preprocessing.scale(rawData['long'])
    # rawData.loc[:, 'lat'] = rawData.loc[:, 'coordinates'].apply(lambda x: x[1])
    # rawData.loc[:, 'lat'] = skl.preprocessing.scale(rawData['lat'])

    # rawData.drop(columns=['coordinates'], inplace=True)
    rawData.reset_index(inplace=True)
    return rawData


def loadData():
    originalData = pd.read_csv('../data/2019-09-27-basel-measures.csv', delimiter=';')
    rawData = originalData.iloc[:, 0:17]
    rawData.loc[:, 'uniqueId'] = rawData['osm_id'].apply(lambda x: str(x)) + "-" + rawData['cci_id'].apply(
        lambda x: str(x))
    rawData.loc[:, 'timestamp'] = rawData.loc[:, 'date'].apply(lambda x: pd.to_datetime(x))
    rawData.loc[:, 'date'] = rawData.loc[:, 'timestamp'].apply(lambda x: x.date())
    rawData.loc[:, 'weekday'] = rawData.loc[:, 'timestamp'].apply(lambda x: x.weekday())
    # hour seems to be plateauish
    # rawData.loc[:, 'hour'] = rawData.loc[:, 'timestamp'].apply(lambda x: x.hour)
    rawData.loc[:, 'time'] = rawData.loc[:, 'timestamp'].apply(lambda x: getTimeCat(x))
    rawData.loc[:, 'isHoliday'] = rawData.loc[:, 'date'].apply(lambda x: getHoliday(x))

    # add weather
    rawData = addWeatherData(rawData)

    # add coordinates
    # rawData = addCoordinates(rawData)

    # add ifWascleaned
    rawData = addIfWasCleaned(rawData)

    return rawData


def getTimeCat(timestamp):
    if timestamp.hour <= 11:
        return 'morning'
    elif timestamp.hour <= 17:
        return 'afternoon'
    else:
        return 'evening'


def initialDataExploration(rawData):
    # number of unique segments rated per day
    tsDates = rawData[['date', 'uniqueId']].groupby('date').count()

    # reports per weekday
    weekDayOccurance = rawData[['weekday', 'uniqueId']].groupby('weekday').count()

    # reports per hour
    hourOccurance = rawData[['hour', 'uniqueId']].groupby('hour').count()

    ### distribution of cleanliness

    # average rating per segment
    averageRating = rawData[['cci', 'uniqueId']].groupby('uniqueId').mean().sort_values('cci')

    # multiple visits per day?
    # rawData[(rawData['date'] == pd.to_datetime('2019-05-11')) & (rawData['osm_id'] == 100699948)]
    # dailyVisits = rawData[['date', 'timestamp', 'uniqueId']].groupby(['uniqueId', 'date']).count()
    # plt.plot(tsDates)


def cleanData(rawData):
    # distribution of # measurements
    measurementsPerId = rawData[['timestamp', 'uniqueId']].groupby('uniqueId').count()
    # plt.hist(measurementsPerId.values, bins=100)
    # clean elements with q<= 0.05
    thresholdValue = measurementsPerId.quantile(0.05).values[0]
    filterLowFrequency = measurementsPerId['timestamp'] >= thresholdValue
    dataWithoutRare = rawData[rawData['uniqueId'].isin(filterLowFrequency[filterLowFrequency].index.tolist())]
    return dataWithoutRare


def transformData(data):
    # collection = 1-places
    # Xcategories = data[['place_type', 'weekday', 'time', 'isHoliday', 'weatherCat', 'long', 'lat']]
    Xcategories = data[['place_type', 'weekday', 'time', 'isHoliday', 'weatherCat', 'wasJustCleaned']]

    features = pd.get_dummies(Xcategories, columns=['place_type', 'weekday', 'time', 'weatherCat'])
    featureNames = list(features.columns)
    scores = data[['cci']]
    return {'features': features, 'featureNames': featureNames, 'scores': scores}


def splitDataSet(transformedData, testSize=0.1):
    # Using Skicit-learn to split data into training and testing sets
    # Split the data into training and testing sets
    train_features, test_features, train_labels, test_labels = train_test_split(np.array(transformedData['features']),
                                                                                np.array(transformedData['scores']),
                                                                                test_size=testSize)
    return train_features, test_features, train_labels, test_labels


def trainAndEvaluateModel(train_features, test_features, train_labels, test_labels):
    # Instantiate model with 1000 decision trees
    rf = RandomForestRegressor(n_estimators=1000, verbose=1, n_jobs=8)
    # Train the model on training data
    rf.fit(train_features, train_labels)

    # Use the forest's predict method on the test data
    predictions = rf.predict(test_features)
    # Calculate the absolute errors
    errors = predictions - test_labels.flatten()
    absoluteError = mean_absolute_error(test_labels.flatten(), predictions)
    squaredError = mean_squared_error(test_labels.flatten(), predictions)

    return {'mae': absoluteError, 'mse': squaredError, 'model': rf}


def trainAndEvaluateWithCV(X, Y):
    model = RandomForestRegressor(n_estimators=100, verbose=1)

    cv = skl.model_selection.KFold(n_splits=10)

    for train_index, test_index in cv.split(X):
        print("TRAIN:", train_index, "TEST:", test_index)
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = Y[train_index], Y[test_index]

        # For training, fit() is used
        model.fit(X_train, y_train)

        # Default metric is R2 for regression, which can be accessed by score()
        model.score(X_test, y_test)

        # For other metrics, we need the predictions of the model
        y_pred = model.predict(X_test)

        print(mean_squared_error(y_test, y_pred))
        print(r2_score(y_test, y_pred))


def deriveWeatherCat(category):
    wClass = 'rain'
    if category in (1, 2):
        wClass = 'sun'
    elif category in (3, 4):
        wClass = 'cloudy'
    elif category == 14:
        wClass = 'thunderstorm'
    return wClass


def calculateAverages(data):
    nameData = data[["uniqueId", "place_name"]].drop_duplicates(['uniqueId']).set_index('uniqueId')
    averagesPerKey = data[
        ["uniqueId", "cci", "rateCigarrettes", "ratePapers", "rateBottles", "rateExcrements", "rateSyringues",
         "rateGums",
         "rateLeaves", "rateGrits", "rateGlassDebris"]].groupby("uniqueId").mean()
    averagesPerKey.loc[:, 'place_name'] = nameData
    return averagesPerKey.reset_index()


def getEvents(date='2019-09-27'):
    with open('../data/events.p', 'rb') as file:
        eventData = pickle.load(file)

    baselEvents = [e for e in eventData if 'basel' in e['address_city'].lower()]
    eventsNow = [e for e in baselEvents if pd.to_datetime(e['date']) == pd.to_datetime('2019-09-27')]
    importantEvents = []
    np.random.seed(12345)
    for e in eventsNow:
        if (e['address_longitude'] is None) or (e['address_latitude'] is None):
            continue

        eventDesc = {'date': date, 'start_time': e['start_time'], 'end_time': e['end_time'],
                     'title': e['title_de'],
                     'desc': e['short_description_de'], 'venue': e['address_venue_name'],
                     'coords': [e['address_longitude'], e['address_latitude']],
                     'attendands': np.random.randint(100, 1500)}
        importantEvents.append(eventDesc)
    return importantEvents


def getMidPoint(cell):
    if isinstance(cell, str) and cell[0] == 'P':
        objectType = 'POLYGON'
    else:
        objectType = 'LINESTRING'

    polystr = cell.split(objectType)[1].strip('(').strip(')').split(", ")
    polygons = [poly.split(" ") for poly in polystr]
    return np.array(polygons).astype(np.float).mean(axis=0)


def addIfWasCleaned(cleanedData):
    routes = pd.read_csv('../data/2019-09-28-basel-sweeper-routes.csv', ';')
    routes.loc[:, 'uniqueId'] = routes['osm_id'].apply(lambda x: str(int(x))) + "-" + routes['cci_id'].apply(lambda x: str(x))
    routes.loc[:, 'date'] = pd.to_datetime(routes['date'])
    cleanedData['wasJustCleaned'] = 0
    for uId in routes['uniqueId'].unique():
        newFrame = cleanedData.loc[cleanedData["uniqueId"] == uId, ["timestamp"]]
        newFrame['lastSweep'] = pd.to_datetime('2019-03-01')
        periodSamples = cleanedData.loc[cleanedData["uniqueId"] == uId, "timestamp"].sort_values()
        periodSweeper = routes.loc[routes["uniqueId"] == uId, "date"].sort_values()
        # for sampleIdx, dateSample in periodSamples.iteritems():
        sampleIdx = 0
        for i in periodSamples.index:
            if periodSamples.loc[i] > periodSweeper.loc[periodSweeper.index[0]]:
                sampleIdx = i
                break
        gen = (idx for idx in periodSamples.index if idx >= sampleIdx)
        for i in gen:
            for j, idxSweep in enumerate(periodSweeper.index):
                    if len(periodSweeper) == j + 1:
                        newFrame.loc[newFrame['timestamp'] == periodSamples.loc[i], 'lastSweep'] = periodSweeper.loc[
                            periodSweeper.index[j - 1]]
                        break
                    elif periodSweeper.loc[idxSweep] <= periodSamples.loc[i]:
                        continue
                    elif (idxSweep > 0) & (j > 0):
                        newFrame.loc[newFrame['timestamp'] == periodSamples.loc[i], 'lastSweep'] = periodSweeper.loc[periodSweeper.index[j-1]]
                        break
        cleanedData.loc[newFrame.index, 'wasJustCleaned'] = cleanedData.loc[newFrame.index, 'timestamp'] - \
                                                            newFrame['lastSweep'] <= pd.to_timedelta(1, 'd')
    return cleanedData


def predictTheLot(cleanedData, model, transformedData):
    unknowns = pd.read_csv('../data/2019-09-27-basel-measures-prediction.csv', ';')
    unknowns = unknowns.iloc[:, 0:3]
    unknowns.loc[:, 'uniqueId'] = unknowns['osm_id'].apply(lambda x: str(int(x))) + "-" + unknowns['cci_id'].apply(lambda x: str(x))

    # create feature for sample to predict
    unknowns.set_index('uniqueId', inplace=True)
    unknowns.drop(columns=['osm_id', 'cci_id'], inplace=True)

    allIds = cleanedData[['uniqueId', 'place_type']].drop_duplicates(['uniqueId']).set_index('uniqueId')
    unknowns.loc[:, 'place_type'] = allIds

    unknowns.loc[:, 'timestamp'] = unknowns.loc[:, 'date'].apply(lambda x: pd.to_datetime(x))
    unknowns.loc[:, 'date'] = unknowns.loc[:, 'timestamp'].apply(lambda x: x.date())
    unknowns.loc[:, 'weekday'] = unknowns.loc[:, 'timestamp'].apply(lambda x: x.weekday())
    # hour seems to be plateauish
    # rawData.loc[:, 'hour'] = rawData.loc[:, 'timestamp'].apply(lambda x: x.hour)
    unknowns.loc[:, 'time'] = unknowns.loc[:, 'timestamp'].apply(lambda x: getTimeCat(x))
    unknowns.loc[:, 'isHoliday'] = unknowns.loc[:, 'date'].apply(lambda x: getHoliday(x))

    # add weather
    unknowns = addWeatherData(unknowns)

    # add ifWascleaned
    unknowns.reset_index(inplace=True)
    unknowns = addIfWasCleaned(unknowns)

    featureData = unknowns[['place_type', 'weekday', 'time', 'isHoliday', 'weatherCat', 'wasJustCleaned']]
    features = pd.get_dummies(featureData, columns=['place_type', 'weekday', 'time', 'weatherCat'])

    transformedColumns = transformedData['featureNames']
    transData = pd.DataFrame(0, columns=transformedColumns, index=features.index)

    for col in features.columns:
        transData.loc[:, col] = features.loc[:, col]

    predictions = model.predict(np.array(transData))
    unknowns.loc[:, "cci"] = predictions

    unknowns.set_index('uniqueId', inplace=True)

    # add name
    nameData = cleanedData[["uniqueId", "place_name"]].drop_duplicates(['uniqueId']).set_index('uniqueId')
    unknowns.loc[:, "place_name"] = nameData

    unknowns.reset_index(inplace=True)
    return unknowns

if __name__ == '__main__':
    rawData = loadData()
    with open('../data/raw.p', 'wb') as file:
        pickle.dump(rawData, file)

    dataWithoutRate = cleanData(rawData)
    with open('../data/cleaned.p', 'wb') as file:
        pickle.dump(dataWithoutRate, file)

    transformedData = transformData(dataWithoutRate)
    with open('../data/transformed.p', 'wb') as file:
        pickle.dump(transformedData, file)

    with open('../data/transformed.p', 'rb') as file:
        transformedData = pickle.load(file)
    # trainAndEvaluateWithCV(transformedData['features'].values, transformedData['scores'].values)

    train_features, test_features, train_labels, test_labels = splitDataSet(transformedData)
    output = trainAndEvaluateModel(train_features, test_features, train_labels, test_labels)
    print(output)

    # # feature importance
    # plt.plot(range(len(output['model'].feature_importances_)), output['model'].feature_importances_)
    # plt.xticks(range(len(output['model'].feature_importances_)), labels=transformedData['featureNames'], rotation='vertical')

    with open('../data/model.p', 'wb') as file:
        pickle.dump(output["model"], file)


def skizzeRareOHOT():
    X_train_rare = copy.copy(X_train)
    X_test_rare = copy.copy(X_test)
    X_train_rare["test"] = 0
    X_test_rare["test"] = 1
    temp_df = pandas.concat([X_train_rare, X_test_rare], axis=0)
    names = list(X_train_rare.columns.values)
    for i in names:
        temp_df.loc[temp_df[i].value_counts()[temp_df[i]].values < 20, i] = "RARE_VALUE"
    for i in range(temp_df.shape[1]):
        temp_df.iloc[:, i] = temp_df.iloc[:, i].astype('str')
    X_train_rare = temp_df[temp_df["test"] == "0"].iloc[:, :-1].values
    X_test_rare = temp_df[temp_df["test"] == "1"].iloc[:, :-1].values
    for i in range(X_train_rare.shape[1]):
        le = preprocessing.LabelEncoder()
        le.fit(temp_df.iloc[:, :-1].iloc[:, i])
        les.append(le)
        X_train_rare[:, i] = le.transform(X_train_rare[:, i])
        X_test_rare[:, i] = le.transform(X_test_rare[:, i])
    enc.fit(X_train_rare)
    X_train_rare = enc.transform(X_train_rare)
    X_test_rare = enc.transform(X_test_rare)
    l.fit(X_train_rare, y_train)
    y_pred = l.predict_proba(X_test_rare)
    print(log_loss(y_test, y_pred))
    r.fit(X_train_rare, y_train)
    y_pred = r.predict_proba(X_test_rare)
    print(log_loss(y_test, y_pred))
    print(X_train_rare.shape)
