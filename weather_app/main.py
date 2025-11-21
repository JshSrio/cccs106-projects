import flet as ft
import asyncio
from weather_service import WeatherService, WeatherServiceError
from config import Config
import json
from pathlib import Path
import speech_recognition as sr
import pyttsx3
import threading

class WeatherApp:
    """Main Weather Application class."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.weather_service = WeatherService()
        self.setup_page()
        self.load_history()
        self.build_ui()
        self.page.scroll= "auto"

    
    def setup_page(self):
        """Configure page settings."""
        self.page.title = Config.APP_TITLE
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN)
        try:
            self.page.bgcolor = ft.Colors.GREY_100
        except Exception:
            pass
        self.page.padding = 20
        self.page.window.width = Config.APP_WIDTH
        self.page.window.height = Config.APP_HEIGHT
        self.page.window.resizable = False
        self.is_dark_mode= False
        self.page.window.center()
    
    def build_ui(self):
        """Build the user interface."""
        # UI state
        self.unit = "metric"
        self.last_weather_data = None
        # Title
        self.title = ft.Text(
            "Weather App",
            size=36,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_900,
        )
        
        # City input field
        self.city_input = ft.TextField(
            label="Enter city name",
            hint_text="e.g., London, Tokyo, New York",
            border_radius=10,
            border_color=ft.Colors.BLUE_400,
            prefix_icon=ft.Icons.LOCATION_CITY,
            autofocus=True,
            on_submit=self.on_search_async,
            on_change=self.on_input_change,
            on_focus=self.on_input_focus,
            on_blur=self.on_input_blur,
            suffix_icon=ft.IconButton(ft.Icons.CLEAR, on_click=self.clear_input),
        )
        
        # Search button
        self.search_button = ft.ElevatedButton(
            "Search",
            icon=ft.Icons.SEARCH,
            on_click=self.on_search_async,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
            ),
        )

        # Weather display container (initially hidden)
        self.weather_container = ft.Container(
            visible=False,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            padding=20,
        )

        # Theme toggle button
        self.theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            tooltip="Toggle theme",
            on_click=self.toggle_theme,
        )

        # Unit toggle buttons (simple segmented style)
        self.unit_toggle_btn = ft.ElevatedButton(
            f"°C",  # initial label
            tooltip="Switch to Fahrenheit",
            on_click=self.toggle_unit,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
            ),
        )

        # Microphone button for voice input
        self.voice_button = ft.IconButton(
            icon=ft.Icons.MIC,
            tooltip="Search city by a voice",
            on_click=self.capture_speech,
        )

        # Error message
        self.error_message = ft.Text(
            "",
            color=ft.Colors.RED_700,
            visible=False,
        )

        # Suggestions container (search history / autocomplete)
        self.suggestions_container = ft.Column([], visible=False, spacing=0)
        
        controls_right = ft.Row([ft.Row([self.unit_toggle_btn], spacing=12), self.theme_button], spacing=12)

        title_row = ft.Row(
            [
                self.title,
                controls_right,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Loading indicator (for requests)
        self.loading = ft.ProgressRing(visible=False)

        # Main column with all components
        main_column = ft.Column(
            [
                title_row,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self.city_input,
                self.suggestions_container,
                self.search_button,
                self.voice_button,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self.loading,
                self.error_message,
                self.weather_container,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
        )

        # Loading overlay
        self.loading_overlay = ft.Container(
            content=ft.ProgressRing(),
            visible=False,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.BLACK,
            opacity=0.5
        )

        try:
            self.set_unit(self.unit)
        except Exception:
            pass

        # Theme switching overlay
        self.theme_loading_overlay = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Text("", size=18, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            ),
            visible=False,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.BLACK,
            opacity=0.7
        )

        self.page.add(ft.Stack([main_column, self.loading_overlay, self.theme_loading_overlay]))
    
    async def on_search_async(self, e):
        """Async event handler."""
        await self.get_weather()

        self.search_button = ft.ElevatedButton(
            "Search",
            on_click=self.on_search_async,
        )

    # ------------------------- Search history helpers -------------------------
    def history_file(self) -> Path:
        return Path(__file__).parent / "search_history.json"

    def load_history(self):
        try:
            path = self.history_file()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except Exception:
            self.history = []

    # ------------------------- Utility / async helpers -------------------------
    def schedule_task(self, coro_or_factory, *args, **kwargs):
        """Schedule a coroutine safely (accepts coroutine or factory).

        Using a factory avoids creating coroutine objects that might never be awaited.
        """
        coro = None
        try:
            if callable(coro_or_factory):
                coro = coro_or_factory(*args, **kwargs)
            else:
                coro = coro_or_factory
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except Exception:
            try:
                if coro is None:
                    return None
                return asyncio.ensure_future(coro)
            except Exception:
                try:
                    if coro is not None:
                        coro.close()
                except Exception:
                    pass
                return None

    def clear_input(self, e=None):
        """Clear the city input field."""
        try:
            self.city_input.value = ""
            self.suggestions_container.controls = []
            self.suggestions_container.visible = False
            self.page.update()
        except Exception:
            pass

    def set_unit(self, unit: str):
        """Set temperature unit ('metric' or 'imperial') and refresh display."""
        if unit not in ("metric", "imperial"):
            return
        self.unit = unit
        # update button visuals if they exist
        try:
            if hasattr(self, 'unit_c_btn') and hasattr(self, 'unit_f_btn'):
                if unit == 'metric':
                    self.unit_c_btn.bgcolor = ft.Colors.WHITE
                    self.unit_c_btn.color = ft.Colors.BLUE_700
                    self.unit_f_btn.bgcolor = ft.Colors.TRANSPARENT
                    self.unit_f_btn.color = ft.Colors.GREY_600
                else:
                    self.unit_f_btn.bgcolor = ft.Colors.WHITE
                    self.unit_f_btn.color = ft.Colors.BLUE_700
                    self.unit_c_btn.bgcolor = ft.Colors.TRANSPARENT
                    self.unit_c_btn.color = ft.Colors.GREY_600
                self.page.update()
        except Exception:
            pass
        try:
            if getattr(self, 'last_weather_data', None):
                self.update_temperature_display(self.last_weather_data)
        except Exception:
            pass

    def update_temperature_display(self, data: dict):
        """Update only the temperature, 'feels like', and wind display texts in-place.

        This avoids hiding or rebuilding the entire weather container when switching units.
        """
        try:
            temp = data.get("main", {}).get("temp", 0)
            feels_like = data.get("main", {}).get("feels_like", 0)
            wind_speed = data.get("wind", {}).get("speed", 0)

            if getattr(self, 'unit', 'metric') == 'imperial':
                display_temp = f"{(temp * 9/5 + 32):.1f}°F"
                display_feels = f"Feels like {(feels_like * 9/5 + 32):.1f}°F"
                wind_display = f"{(wind_speed * 2.236936):.1f} mph"
            else:
                display_temp = f"{temp:.1f}°C"
                display_feels = f"Feels like {feels_like:.1f}°C"
                wind_display = f"{wind_speed:.1f} m/s"

            col = getattr(self.weather_container, 'content', None)
            if isinstance(col, ft.Column):
                controls = col.controls
                if len(controls) >= 4:
                    temp_text = controls[2]
                    feels_text = controls[3]
                    try:
                        temp_text.value = display_temp
                    except Exception:
                        try:
                            temp_text.text = display_temp
                        except Exception:
                            pass
                    try:
                        feels_text.value = display_feels
                    except Exception:
                        try:
                            feels_text.text = display_feels
                        except Exception:
                            pass

                if len(controls) >= 6:
                    info_row = controls[5]
                    try:
                        if isinstance(info_row, ft.Row) and len(info_row.controls) >= 2:
                            card2 = info_row.controls[1]
                            inner_col = getattr(card2, 'content', None)
                            if isinstance(inner_col, ft.Column) and len(inner_col.controls) >= 3:
                                wind_text = inner_col.controls[2]
                                try:
                                    wind_text.value = wind_display
                                except Exception:
                                    try:
                                        wind_text.text = wind_display
                                    except Exception:
                                        pass
                    except Exception:
                        pass

            # keep the weather container visible
            if hasattr(self, 'weather_container'):
                self.weather_container.visible = True
            self.page.update()
        except Exception:
            pass

    def show_mode_loader(self):
        """Show the semi-transparent overlay with a spinner (if present)."""
        try:
            if hasattr(self, 'mode_overlay'):
                self.mode_overlay.visible = True
                self.page.update()
        except Exception:
            pass

    async def _hide_mode_loader_after(self, seconds: float = 0.5):
        await asyncio.sleep(seconds)
        try:
            if hasattr(self, 'mode_overlay'):
                self.mode_overlay.visible = False
                self.page.update()
        except Exception:
            pass

    async def _fade_in_weather(self):
        await asyncio.sleep(0.1)
        try:
            self.weather_container.opacity = 1
            self.page.update()
        except Exception:
            pass

    def save_history(self):
        try:
            path = self.history_file()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def update_history(self, city: str):
        if not city:
            return
        city_norm = city.strip()
        # avoid duplicates (case-insensitive)
        existing = next((h for h in self.history if h.lower() == city_norm.lower()), None)
        if existing:
            self.history.remove(existing)
            self.history.insert(0, existing)
        else:
            self.history.insert(0, city_norm)
        # keep reasonable history length
        self.history = self.history[:50]
        self.save_history()
        # history updated; inline suggestions will reflect changes

    # ------------------------- Input / suggestion handlers -------------------------
    def on_input_focus(self, e):
        self.input_focused = True
        self.on_input_change(e)

    def on_input_blur(self, e):
        self.input_focused = False
        self.suggestions_container.controls = []
        self.suggestions_container.visible = False
        self.page.update()

    def make_suggestion_handler(self, suggestion: str):
        def handler(e):
            try:
                self.city_input.value = suggestion
                self.suggestions_container.visible = False
                self.page.update()
                try:
                    self.schedule_task(self.get_weather)
                except Exception:
                    import asyncio
                    asyncio.create_task(self.get_weather())
            except Exception:
                pass
        return handler

    def on_input_change(self, e):
        value = (e.control.value or "").strip()
        if not value or not getattr(self, "input_focused", True):
            self.suggestions_container.controls = []
            self.suggestions_container.visible = False
            self.page.update()
            return

        matches = [h for h in self.history if value.lower() in h.lower()]
        if not matches:
            matches = list(self.history)

        # show up to last 5
        matches = matches[:5]

        controls = []
        for h in matches:
            controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.HISTORY, size=18, color=ft.Colors.GREY_600),
                    title=ft.Text(h),
                    on_click=self.make_suggestion_handler(h),
                    content_padding=ft.Padding(8, 4, 8, 4),
                )
            )

        self.suggestions_container.controls = controls
        self.suggestions_container.visible = True
        self.page.update()
    
    async def get_weather(self):
        """Fetch and display weather data."""
        city = self.city_input.value.strip()
        
        # Validate input
        if not city:
            self.show_error("Please enter a city name")
            return
        
        # Show loading, hide previous results
        self.loading.visible = True
        self.error_message.visible = False
        self.weather_container.visible = False
        self.page.update()
        
        try:
            # Fetch weather data
            weather_data = await self.weather_service.get_weather(city)
            
            # Display weather
            self.display_weather(weather_data)

        except WeatherServiceError as e:
            self.show_error(str(e))
            
        except Exception as e:
            self.show_error("An unexpected error occured. Please try again.")
        
        finally:
            self.loading.visible = False
            self.page.update()

    # ----------------- Voice recognition -----------------
    def schedule_voice_search(self, e):
        """Schedule the async voice capture."""
        self.schedule_task(self.capture_speech)

    
    async def capture_speech(self, e):
        recognizer = sr.Recognizer()
        self.show_error("Listening...")
        self.page.update()

        try:
            # Run blocking microphone listening in a separate thread
            audio = await asyncio.to_thread(self.listen_microphone, recognizer)
            try:
                city_name = recognizer.recognize_google(audio)
                self.city_input.value = city_name
                self.page.update()
                await self.get_weather()  # fetch weather after recognition
            except sr.UnknownValueError:
                self.show_error("Could not understand audio")
                self.page.update()
            except sr.RequestError:
                self.show_error("Speech service unavailable")
                self.page.update()
        except Exception:
            self.show_error("Microphone error")
            self.page.update()
        finally:
            # Hide temporary message after 2 sec
            await asyncio.sleep(2)
            self.error_message.visible = False
            self.page.update()

    def listen_microphone(self, recognizer):
        """Blocking call for listening."""
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=5)
        return audio

    # ----------------- Voice feedback -----------------
    def speak_text(self, text: str):
        """Run TTS in a separate thread to avoid blocking UI."""
        def tts_thread():
            try:
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

        threading.Thread(target=tts_thread, daemon=True).start()
        
    def display_weather(self, data: dict):
        """Display weather information."""
        # Extract data
        city_name = data.get("name", "Unknown")
        country = data.get("sys", {}).get("country", "")
        temp = data.get("main", {}).get("temp", 0)
        feels_like = data.get("main", {}).get("feels_like", 0)
        humidity = data.get("main", {}).get("humidity", 0)
        description = data.get("weather", [{}])[0].get("description", "").title()
        icon_code = data.get("weather", [{}])[0].get("icon", "01d")
        wind_speed = data.get("wind", {}).get("speed", 0)
        unit = "Celsius" if self.unit == "metric" else "Fahrenheit"

        
        if getattr(self, 'unit', 'metric') == 'imperial':
            wind_display = f"{(wind_speed * 2.236936):.1f} mph"
        else:
            wind_display = f"{wind_speed:.1f} m/s"

        try:
            self.last_weather_data = data
        except Exception:
            pass

        # --- Display temperature in selected unit ---
        if self.unit == "imperial":
            display_temp = f"{temp*9/5 + 32:.1f}°F"
            display_feels = f"Feels like {feels_like*9/5 + 32:.1f}°F"
        else:
            display_temp = f"{temp:.1f}°C"
            display_feels = f"Feels like {feels_like:.1f}°C"
            
        # Build weather display
        self.weather_container.content = ft.Column(
            [
                # Location
                ft.Text(
                    f"{city_name}, {country}",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                
                # Weather icon and description
                ft.Row(
                    [
                        ft.Image(
                            src=f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
                            width=100,
                            height=100,
                        ),
                        ft.Text(
                            description,
                            size=20,
                            italic=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                
                # Temperature
                ft.Text(
                    display_temp,
                    size=48,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900,
                ),
                
                ft.Text(
                    display_feels,
                    size=16,
                    color=ft.Colors.GREY_700,
                ),
                
                ft.Divider(),
                
                # Additional info
                ft.Row(
                    [
                        self.create_info_card(
                            ft.Icons.WATER_DROP,
                            "Humidity",
                            f"{humidity}%"
                        ),
                        self.create_info_card(
                            ft.Icons.AIR,
                            "Wind Speed",
                            wind_display
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )
        
        self.weather_container.animate_opacity = 300
        self.weather_container.opacity = 0
        self.weather_container.visible = True
        self.error_message.visible = False
        self.page.update()

        try:
            self.schedule_task(self._fade_in_weather)
        except Exception:
            self.weather_container.opacity = 1
            self.page.update()

        try:
            self.update_history(city_name)
        except Exception:
            pass

        message = f"The Weather in {city_name}: {description}, temperature {display_temp}"
        self.speak_text(message)

    def setup_page(self):
        """Configure page settings."""
        self.page.title = Config.APP_TITLE
        
        # Add theme switcher
        self.page.theme_mode = ft.ThemeMode.SYSTEM  # Use system theme
        
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
        )
        
        self.page.padding = 20
        
        self.page.window.width = Config.APP_WIDTH
        self.page.window.height = Config.APP_HEIGHT
        self.page.window.resizable = False
        self.page.window.center()

    def toggle_theme(self, e):
        """Toggle between light and dark theme."""
        try:
            self.show_mode_loader()
        except Exception:
            pass

        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_button.icon = ft.Icons.LIGHT_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_button.icon = ft.Icons.DARK_MODE

        new_color = ft.Colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.WHITE
        self.title.color = new_color

        self.page.update()

        try:
            self.schedule_task(self._hide_mode_loader_after, 0.6)
        except Exception:
            pass
    
    def create_info_card(self, icon, label, value):
        """Create an info card for weather details."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, size=30, color=ft.Colors.BLUE_700),
                    ft.Text(label, size=12, color=ft.Colors.GREY_600),
                    ft.Text(
                        value,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_900,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            padding=15,
            width=150,

        )
    
    def toggle_unit(self, e):
        """Switch between Celsius and Fahrenheit with dynamic tooltip."""
        if self.unit == "metric":
            self.unit = "imperial"
            self.unit_toggle_btn.text = "°F"
            self.unit_toggle_btn.tooltip = "Switch to Celsius"
        else:
            self.unit = "metric"
            self.unit_toggle_btn.text = "°C"
            self.unit_toggle_btn.tooltip = "Switch to Fahrenheit"

        if self.last_weather_data:
            self.update_temperature_display(self.last_weather_data)
        self.page.update()

    async def switch_theme_with_loading(self):
        if self.is_dark_mode:
            message = "Switching to light mode..."
        else:
            message = "Switching to dark mode..."
        
        self.theme_loading_overlay.content.controls[1].value = message
        self.theme_loading_overlay.visible = True
        self.page.update()
        
        # Wait briefly for effect
        await asyncio.sleep(0.8)
        
        # Switch theme
        self.is_dark_mode = not self.is_dark_mode
        self.page.theme_mode = ft.ThemeMode.DARK if self.is_dark_mode else ft.ThemeMode.LIGHT
        
        self.theme_loading_overlay.visible = False
        self.page.update()


    
    def show_error(self, message: str):
        """Display error message."""
        self.error_message.value = f"❌ {message}"
        self.error_message.visible = True
        self.weather_container.visible = False
        self.page.update()


def main(page: ft.Page):
    """Main entry point."""
    WeatherApp(page)


if __name__ == "__main__":
    ft.app(target=main)