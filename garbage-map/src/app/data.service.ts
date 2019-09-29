import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {map, tap} from 'rxjs/operators';
import {HttpClient} from '@angular/common/http';
import {Event} from './event.interface';
import {Place} from './place.interface';
import { Average } from './average.interface';

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private places: Observable<any[]>;
  private events: Observable<any[]>;
  private placesUrl = 'http://localhost:5000/predict/';
  private averagesUrl = 'http://localhost:5000/averages';
  private eventsUrl = 'http://localhost:5000/events/2019-09-25';

  constructor(private http: HttpClient) {
    this.http = http;
  }

  getPlaces(time: string): Observable<Place[]> {
    console.log('getplaces dataservice call', this.placesUrl + time);
    return this.http.get<Place[]>(this.placesUrl + time).pipe(
      map(data => {
        return data.map(place => {
          return {
            coordinates: place.coordinates,
            type: place.place_type,
            weekday: place.weekday,
            time: place.time,
            isHoliday: place.isHoliday,
            weatherCat: place.weatherCat,
            cci: place.cci,
            name: place.place_name
          } as Place;
        });
      }),
    );
  }

  getAverages(): Observable<Average[]> {
    console.log('getaverages dataservice call');
    return this.http.get<Average[]>(this.averagesUrl).pipe(
      map(data => {
        return data.map(average => {
          return {
            coordinates: average.coordinates,
            cci: average.cci,
            name: average.place_name,
            rateCigarrettes: average.rateCigarrettes,
            rateBottles: average.rateBottles,
            ratePapers: average.ratePapers,
            rateExcrements: average.rateExcrements,
            rateSyringues: average.rateSyringues,
            rateGums: average.rateGums,
            rateLeaves: average.rateLeaves,
            rateGrits: average.rateGrits,
            rateGlassDebris: average.rateGlassDebris
          } as Average;
        });
      }),
      tap(res=>console.log(res))
    );
  }

  getEvents(): Observable<Event[]> {
    return this.http.get<Event[]>(this.eventsUrl).pipe(
      map(data => {
        return data.map(event => {
          return {
            date: event.date,
            start_time: event.start_time,
            end_time: event.end_time,
            title: event.title,
            desc: event.desc,
            venue: event.venue,
            coords: event.coords,
            attendands: event.attendands
          } as Event;
        });
      }),
      tap(res => console.log(res))
    );
  }

  getDataByDay($eventElement: string): Observable<Place[]> {
    const url = `${this.placesUrl}`;
    return this.http.get<Place[]>(url).pipe(
      tap(_ => console.log(`fetched data with date ${$eventElement}`))
    );
  }
}
