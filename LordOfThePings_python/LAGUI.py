# Import customtkinter module
import customtkinter as ctk
import tkinter as tk

# Sets the appearance mode of the application
# "System" sets the appearance same as that of the system
ctk.set_appearance_mode("System")

# Sets the color of the widgets
# Supported themes: green, dark-blue, blue
ctk.set_default_color_theme("green")
appWidth, appHeight = 600, 700
# Create App class
class App(ctk.CTk):
# Layout of the GUI will be written in the init itself
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
# Sets the title of our window to "App"
        self.title("Lord-Of-The-Pings")
# Dimensions of the window will be 200x200
        self.geometry(f"{appWidth}x{appHeight}")


        self.generateResultsButton = ctk.CTkButton(self,
                                                   text="Generate Results")
        self.generateResultsButton.grid(row=5, column=1,
                                        columnspan=2,
                                        padx=215, pady=20,
                                        sticky="ew")

if __name__ == "__main__":
    app = App()
    # Runs the app
    app.mainloop()