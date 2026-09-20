export type Weather = {
  tempC: number
  condition: string
  location: string
}

export async function fetchWeather(): Promise<Weather> {
  try {
    const res = await fetch(
      'https://api.open-meteo.com/v1/forecast?latitude=47.97&longitude=-122.2&current_weather=true'
    )
    if (!res.ok) throw new Error('weather-failed')
    const data = await res.json()
    const current = data.current_weather
    return {
      tempC: Math.round(current.temperature),
      condition: mapWeatherCode(current.weathercode),
      location: 'Everett, WA',
    }
  } catch {
    return { tempC: 17, condition: 'clear', location: 'Everett, WA' }
  }
}

function mapWeatherCode(code: number) {
  if (code === 0) return 'clear'
  if ([1, 2, 3].includes(code)) return 'cloudy'
  if ([45, 48].includes(code)) return 'fog'
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return 'rain'
  if ([71, 73, 75, 77, 85, 86].includes(code)) return 'snow'
  return 'clear'
}
