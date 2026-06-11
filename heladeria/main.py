from db.database import init_db
from ui.main_window import MainWindow

if __name__ == "__main__":
    init_db()
    app = MainWindow()
    app.mainloop()
