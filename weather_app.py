import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date
import altair as alt

# Setup the Open-Meteo API client with cache and retry on error
@st.cache_resource
def setup_openmeteo():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)

openmeteo = setup_openmeteo()

# Function to fetch weather data
@st.cache_data(ttl=3600)
def fetch_weather_data(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "rain", "showers", "snowfall", "is_day", "weather_code"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability", "cloud_cover"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "sunrise", "sunset"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",
        "forecast_days": 14
    }
    responses = openmeteo.weather_api(url, params=params)
    return responses[0]

# Streamlit app
st.title('Weather Forecast App')

# User input for location
latitude = st.number_input('Latitude', value=36.1676029)
longitude = st.number_input('Longitude', value=-86.8521476)

if st.button('Fetch Weather Data'):
    response = fetch_weather_data(latitude, longitude)

    # Display current weather
    st.header('Current Weather')
    current = response.Current()
    st.write(f"Temperature: {current.Variables(0).Value():.1f}°F")
    st.write(f"Relative Humidity: {current.Variables(1).Value():.1f}%")
    st.write(f"Apparent Temperature: {current.Variables(2).Value():.1f}°F")
    st.write(f"Precipitation: {current.Variables(3).Value():.2f} inches")
    st.write(f"Rain: {current.Variables(4).Value():.2f} inches")
    st.write(f"Showers: {current.Variables(5).Value():.2f} inches")
    st.write(f"Snow: {current.Variables(6).Value():.2f} inches")
    st.write(f"IsDay: {current.Variables(7).Value()}")
    st.write(f"WeatherCode: {current.Variables(8).Value()}")

    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "Temp": hourly.Variables(0).ValuesAsNumpy(),
        "Relative Humidity": hourly.Variables(1).ValuesAsNumpy(),
        "Dew Point": hourly.Variables(2).ValuesAsNumpy(),
        "Apparent Temperature": hourly.Variables(3).ValuesAsNumpy(),
        "Precipitation Probability": hourly.Variables(4).ValuesAsNumpy(),
        "Cloud Cover": hourly.Variables(5).ValuesAsNumpy()
    }
    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Process daily data
    daily = response.Daily()
    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        ),
        "Temp Max": daily.Variables(0).ValuesAsNumpy(),
        "Temp Min": daily.Variables(1).ValuesAsNumpy(),
        "Apparent Temp Max": daily.Variables(2).ValuesAsNumpy(),
        "Apparent Temp Min": daily.Variables(3).ValuesAsNumpy(),
        "sunrise": daily.Variables(4).ValuesAsNumpy(),
        "sunset": daily.Variables(5).ValuesAsNumpy()
    }
    daily_dataframe = pd.DataFrame(data=daily_data)

       # Plot daily forecast
    st.header('Daily Temperature Forecast')

    # Melt the dataframe to long format for Altair
    daily_long = pd.melt(daily_dataframe, 
                         id_vars=['date'], 
                         value_vars=['Temp Max', 'Temp Min', 
                                     'Apparent Temp Max', 'Apparent Temp Min'],
                         var_name='Measure', value_name='Temperature')

    # Create the Altair chart
    daily_chart = alt.Chart(daily_long).mark_line(point=True).encode(
        x=alt.X('date:T', axis=alt.Axis(format='%Y-%m-%d', labelAngle=-45, title='Date')),
        y=alt.Y('Temperature:Q', axis=alt.Axis(title='Temperature (°F)')),
        color=alt.Color('Measure:N', legend=alt.Legend(title="Measure")),
        tooltip=['date:T', 'Measure:N', 'Temperature:Q']
    ).properties(
        width=800,
        height=400,
        title='Daily Temperature Forecast'
    ).interactive()

    # Customize the legend
    daily_chart = daily_chart.configure_legend(
        orient='bottom',
        labelFontSize=12,
        titleFontSize=14
    )

    st.altair_chart(daily_chart, use_container_width=True)

    # Plot hourly forecast
    st.header('Hourly Forecast (Next 48 Hours)')
    end_date = date.today() + timedelta(days=2)
    hourly_dataframe = hourly_dataframe.loc[hourly_dataframe['date'].dt.date < end_date]

    # Melt the dataframe to long format for Altair
    hourly_long = pd.melt(hourly_dataframe, id_vars=['date'], 
                          value_vars=['Temp', 'Relative Humidity', 'Dew Point', 
                                      'Apparent Temperature', 'Precipitation Probability'],
                          var_name='Measure', value_name='Value')

    # Create the Altair chart
    chart = alt.Chart(hourly_long).mark_line().encode(
        x=alt.X('date:T', axis=alt.Axis(format='%Y-%m-%d %H:%M', labelAngle=-90)),
        y='Value:Q',
        color='Measure:N',
        tooltip=['date:T', 'Measure:N', 'Value:Q']
    ).properties(
        width=800,
        height=400
    ).interactive()
    
    # Customize the legend
    chart = chart.configure_legend(
        orient='bottom',
        labelFontSize=12,
        titleFontSize=14
    )
    st.altair_chart(chart, use_container_width=True)
