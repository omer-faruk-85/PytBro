import sys
import json
import csv
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFormLayout,
    QListWidget,
    QDockWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QTabWidget,
    QFileDialog,
    QLabel,
    QMenuBar,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction, QClipboard


class WebEngineView(QWebEngineView):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    def createWindow(self, _type):
        return self.browser.create_new_tab()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        new_tab_action = QAction("Open in New Tab", self)
        new_window_action = QAction("Open in New Window", self)
        menu.addAction(new_tab_action)
        menu.addAction(new_window_action)

        def open_in_new_tab():
            context_menu_data = self.page().contextMenuData()
            link_url = context_menu_data.linkUrl()
            if link_url.isValid():
                self.browser.create_new_tab(link_url.toString())

        def open_in_new_window():
            context_menu_data = self.page().contextMenuData()
            link_url = context_menu_data.linkUrl()
            if link_url.isValid():
                self.browser.create_new_window(link_url.toString())

        new_tab_action.triggered.connect(open_in_new_tab)
        new_window_action.triggered.connect(open_in_new_window)

        menu.exec_(self.mapToGlobal(event.pos()))


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Web Browser")
        self.setGeometry(100, 100, 1200, 800)

        self.passwords = {}  # Initialize the passwords attribute

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL and press Enter")
        self.url_bar.returnPressed.connect(self.navigate_to_url)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        self.setCentralWidget(self.tabs)

        self.new_tab_button = QToolButton()
        self.new_tab_button.setText("+")
        self.new_tab_button.clicked.connect(self.create_new_tab)
        self.tabs.setCornerWidget(self.new_tab_button, Qt.TopRightCorner)

        self.create_new_tab("https://www.google.com")

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(lambda: self.tabs.currentWidget().back())

        self.forward_button = QPushButton("Forward")
        self.forward_button.clicked.connect(lambda: self.tabs.currentWidget().forward())

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(lambda: self.tabs.currentWidget().reload())

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.navigate_to_url)

        self.add_to_bookmark_button = QPushButton("Add to Bookmarks")
        self.add_to_bookmark_button.clicked.connect(self.add_bookmark)

        # Menü düğmesini oluştur
        self.menu_button = QToolButton()
        self.menu_button.setText("Options")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)

        self.menu = QMenu(self)

        self.toggle_bookmarks_action = QAction("Toggle Bookmarks", self)
        self.toggle_bookmarks_action.triggered.connect(self.toggle_bookmarks)

        self.toggle_passwords_action = QAction("Toggle Passwords", self)
        self.toggle_passwords_action.triggered.connect(self.toggle_passwords)

        self.import_passwords_action = QAction("Import Passwords", self)
        self.import_passwords_action.triggered.connect(self.import_passwords)

        self.export_passwords_action = QAction("Export Passwords", self)
        self.export_passwords_action.triggered.connect(self.export_passwords)

        self.menu.addAction(self.toggle_bookmarks_action)
        self.menu.addAction(self.toggle_passwords_action)
        self.menu.addAction(self.import_passwords_action)
        self.menu.addAction(self.export_passwords_action)

        self.menu_button.setMenu(self.menu)

        nav_bar = QHBoxLayout()
        nav_bar.addWidget(self.back_button)
        nav_bar.addWidget(self.forward_button)
        nav_bar.addWidget(self.reload_button)
        nav_bar.addWidget(self.url_bar)
        nav_bar.addWidget(self.go_button)
        nav_bar.addWidget(self.add_to_bookmark_button)
        nav_bar.addWidget(self.menu_button)

        nav_container = QWidget()
        nav_container.setLayout(nav_bar)

        main_layout = QVBoxLayout()
        main_layout.addWidget(nav_container)
        main_layout.addWidget(self.tabs)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.bookmarks_file = "bookmarks.json"
        self.passwords_file = "passwd.json"

        self.create_docks()
        self.load_data()

    def create_new_tab(self, url="https://www.google.com"):
        browser = WebEngineView(self)
        browser.setUrl(QUrl(url))
        index = self.tabs.addTab(browser, "New Tab")
        self.tabs.setCurrentIndex(index)
        browser.urlChanged.connect(
            lambda qurl, browser=browser: self.update_url_bar(qurl, browser)
        )
        browser.loadFinished.connect(
            lambda _, i=index, browser=browser: self.tabs.setTabText(
                i, browser.page().title()
            )
        )
        return browser

    def create_new_window(self, url="https://www.google.com"):
        new_browser = Browser()
        new_browser.show()
        new_browser.create_new_tab(url)

    def current_tab_changed(self, index):
        if index != -1:
            qurl = self.tabs.currentWidget().url()
            self.update_url_bar(qurl, self.tabs.currentWidget())

    def tab_open_doubleclick(self, index):
        if index == -1:
            self.create_new_tab()

    def close_current_tab(self, index):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(index)

    def update_url_bar(self, qurl, browser=None):
        if browser != self.tabs.currentWidget():
            return
        self.url_bar.setText(qurl.toString())
        self.autofill_password(qurl)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith("http"):
            url = "http://" + url
        self.tabs.currentWidget().setUrl(QUrl(url))
        self.autofill_password(QUrl(url))

    def create_docks(self):
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.itemClicked.connect(self.load_bookmark)

        self.bookmarks_dock = QDockWidget("Bookmarks", self)
        self.bookmarks_dock.setWidget(self.bookmarks_list)
        self.bookmarks_dock.setFloating(False)
        self.bookmarks_dock.hide()

        self.passwords_list = QListWidget()
        self.passwords_list.itemClicked.connect(self.load_password)

        self.passwords_dock = QDockWidget("Passwords", self)
        self.passwords_dock.setWidget(self.passwords_list)
        self.passwords_dock.setFloating(False)
        self.passwords_dock.hide()

        self.addDockWidget(Qt.RightDockWidgetArea, self.bookmarks_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.passwords_dock)

    def toggle_bookmarks(self):
        if self.bookmarks_dock.isVisible():
            self.bookmarks_dock.hide()
        else:
            self.bookmarks_dock.show()

    def toggle_passwords(self):
        if self.passwords_dock.isVisible():
            self.passwords_dock.hide()
        else:
            self.passwords_dock.show()

    def add_bookmark(self):
        current_url = self.tabs.currentWidget().url().toString()
        if current_url:
            self.create_bookmark_item(current_url)
            self.save_data()

    def create_bookmark_item(self, url):
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(0, 0, 0, 0)

        url_label = QLineEdit(url)
        url_label.setReadOnly(True)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self.remove_bookmark_item(item_widget))

        item_layout.addWidget(url_label)
        item_layout.addWidget(delete_button)
        item_widget.setLayout(item_layout)

        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())

        self.bookmarks_list.addItem(list_item)
        self.bookmarks_list.setItemWidget(list_item, item_widget)

    def remove_bookmark_item(self, item_widget):
        for index in range(self.bookmarks_list.count()):
            list_item = self.bookmarks_list.item(index)
            if self.bookmarks_list.itemWidget(list_item) == item_widget:
                self.bookmarks_list.takeItem(index)
                self.save_data()
                break

    def load_bookmark(self, item):
        self.tabs.currentWidget().setUrl(QUrl(item.text()))

    def load_password(self, item):
        item_widget = self.passwords_list.itemWidget(item)
        url = item_widget.findChild(QLabel, "url_label").text()
        username = item_widget.findChild(QLabel, "username_label").text()
        password = item_widget.findChild(QLabel, "password_label").text()

        clipboard = QApplication.clipboard()
        clipboard.setText(f"{username}\n{password}")

        self.tabs.currentWidget().setUrl(QUrl(url))

    def create_password_item(self, name, url, username, password, note):
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(0, 0, 0, 0)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(lambda: self.copy_credentials(username, password))

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self.remove_password_item(item_widget))

        item_layout.addWidget(copy_button)
        item_layout.addWidget(delete_button)

        form_layout = QFormLayout()
        name_label = QLabel(name)
        url_label = QLabel(url)
        username_label = QLabel(username)
        password_label = QLabel(password)
        note_label = QLabel(note)

        url_label.setObjectName("url_label")
        username_label.setObjectName("username_label")
        password_label.setObjectName("password_label")

        form_layout.addRow("Name:", name_label)
        form_layout.addRow("URL:", url_label)
        form_layout.addRow("Username:", username_label)
        form_layout.addRow("Password:", password_label)
        form_layout.addRow("Note:", note_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(item_layout)
        main_layout.addLayout(form_layout)
        item_widget.setLayout(main_layout)

        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())

        self.passwords_list.addItem(list_item)
        self.passwords_list.setItemWidget(list_item, item_widget)

    def copy_credentials(self, username, password):
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{username}\n{password}")

    def remove_password_item(self, item_widget):
        for index in range(self.passwords_list.count()):
            list_item = self.passwords_list.item(index)
            if self.passwords_list.itemWidget(list_item) == item_widget:
                url = item_widget.findChild(QLabel, "url_label").text()
                del self.passwords[url]
                self.passwords_list.takeItem(index)
                self.save_data()
                break

    def load_data(self):
        try:
            with open(self.bookmarks_file, "r") as file:
                bookmarks = json.load(file)
                for bookmark in bookmarks:
                    self.create_bookmark_item(bookmark)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        try:
            with open(self.passwords_file, "r") as file:
                self.passwords = json.load(file)
                for url, details in self.passwords.items():
                    self.create_password_item(
                        details["name"],
                        url,
                        details["username"],
                        details["password"],
                        details["note"],
                    )
        except (FileNotFoundError, json.JSONDecodeError):
            self.passwords = {}

    def save_data(self):
        bookmarks = []
        for index in range(self.bookmarks_list.count()):
            list_item = self.bookmarks_list.item(index)
            url_widget = (
                self.bookmarks_list.itemWidget(list_item).layout().itemAt(0).widget()
            )
            bookmarks.append(url_widget.text())

        with open(self.bookmarks_file, "w") as file:
            json.dump(bookmarks, file)

        with open(self.passwords_file, "w") as file:
            json.dump(self.passwords, file)

    def import_passwords(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Passwords CSV", "", "CSV Files (*.csv)"
        )
        if file_name:
            with open(file_name, mode="r") as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    if (
                        "name" in row
                        and "url" in row
                        and "username" in row
                        and "password" in row
                        and "note" in row
                    ):
                        self.passwords[row["url"]] = {
                            "name": row["name"],
                            "username": row["username"],
                            "password": row["password"],
                            "note": row["note"],
                        }
                        self.create_password_item(
                            row["name"],
                            row["url"],
                            row["username"],
                            row["password"],
                            row["note"],
                        )
                self.save_data()

    def export_passwords(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Passwords CSV", "", "CSV Files (*.csv)"
        )
        if file_name:
            with open(file_name, mode="w", newline="") as file:
                fieldnames = ["name", "url", "username", "password", "note"]
                csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
                csv_writer.writeheader()
                for url, details in self.passwords.items():
                    row = {
                        "name": details["name"],
                        "url": url,
                        "username": details["username"],
                        "password": details["password"],
                        "note": details["note"],
                    }
                    csv_writer.writerow(row)

    def autofill_password(self, qurl):
        site = qurl.host()
        for url, details in self.passwords.items():
            if site in url:
                script = f"""
                document.querySelector('input[type="text"]').value = '{details["username"]}';
                document.querySelector('input[type="password"]').value = '{details["password"]}';
                """
                self.tabs.currentWidget().page().runJavaScript(script)
                break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Browser()
    browser.show()
    sys.exit(app.exec())
