import React, { useEffect, useState } from 'react';

const Weather = () => {
    const [weather, setWeather] = useState(null);

    useEffect(() => {
        const fetchWeather = async () => {
            try {
                const response = await fetch('https://api.open-meteo.com/v1/forecast?latitude=37.7749&longitude=-122.4194&current_weather=true');
                const data = await response.json();
                setWeather(data.current_weather);
            } catch (error) {
                console.error('Error fetching weather data:', error);
            }
        };

        fetchWeather();
    }, []);

    if (!weather) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>Weather in San Francisco</h1>
            <p>Temperature: {weather.temperature}°C</p>
            <p>Wind Speed: {weather.windspeed} km/h</p>
        </div>
    );
};

export default Weather;
