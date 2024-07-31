import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date
from aquarel import load_theme
set_theme = "minimal_dark"

theme = load_theme(set_theme)
theme.apply()

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
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "rain", "showers", "snowfall"],
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

    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
        "dew_point_2m": hourly.Variables(2).ValuesAsNumpy(),
        "apparent_temperature": hourly.Variables(3).ValuesAsNumpy(),
        "precipitation_probability": hourly.Variables(4).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(5).ValuesAsNumpy()
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
        "temperature_2m_max": daily.Variables(0).ValuesAsNumpy(),
        "temperature_2m_min": daily.Variables(1).ValuesAsNumpy(),
        "apparent_temperature_max": daily.Variables(2).ValuesAsNumpy(),
        "apparent_temperature_min": daily.Variables(3).ValuesAsNumpy(),
        "sunrise": daily.Variables(4).ValuesAsNumpy(),
        "sunset": daily.Variables(5).ValuesAsNumpy()
    }
    daily_dataframe = pd.DataFrame(data=daily_data)

    # Plot daily forecast
    st.header('Daily Temperature Forecast')
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.plot(daily_dataframe['date'], daily_dataframe['temperature_2m_max'], label='Max Temperature')
    ax.plot(daily_dataframe['date'], daily_dataframe['temperature_2m_min'], label='Min Temperature')
    ax.plot(daily_dataframe['date'], daily_dataframe['apparent_temperature_max'], label='Max Apparent Temperature', linestyle='--')
    ax.plot(daily_dataframe['date'], daily_dataframe['apparent_temperature_min'], label='Min Apparent Temperature', linestyle='--')
    ax.set_xlabel('Date')
    ax.set_ylabel('Temperature (°F)')
    ax.legend(loc='upper right', edgecolor='grey', framealpha=0.5, shadow=True, fancybox=True)
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=90, ha='center')
    plt.tight_layout()
    st.pyplot(fig)

    # Plot hourly forecast
    st.header('Hourly Forecast (Next 48 Hours)')
    end_date = date.today() + timedelta(days=2)
    hourly_dataframe = hourly_dataframe.loc[hourly_dataframe['date'].dt.date < end_date]

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.plot(hourly_dataframe['date'], hourly_dataframe['temperature_2m'], label='Temperature')
    ax.plot(hourly_dataframe['date'], hourly_dataframe['relative_humidity_2m'], label='Relative Humidity')
    ax.plot(hourly_dataframe['date'], hourly_dataframe['dew_point_2m'], label='Dew Point')
    ax.plot(hourly_dataframe['date'], hourly_dataframe['apparent_temperature'], label='Apparent Temperature')
    ax.plot(hourly_dataframe['date'], hourly_dataframe['precipitation_probability'], label='Precip. Probability', linestyle='--')
    ax.set_xlabel('When')
    ax.set_ylabel('Temperature (°F)')
    ax.legend(loc='upper right', edgecolor='grey', framealpha=0.5, shadow=True, fancybox=True)
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=90, ha='center')
    plt.tight_layout()
    st.pyplot(fig)
