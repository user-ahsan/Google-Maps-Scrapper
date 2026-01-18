# End User Setup Guide 🛠️

This guide is for **Installation & Configuration** of the Google Maps Scraper Pro. It focuses on the one-time setup required to get the application running on your Windows machine.

## 📋 Prerequisites
Before you start, you need:
1.  **GoogleMapsScraper.exe** (The application file).
2.  A Google Account (gmail) to create the Google Sheets API key.

---

## 🔑 Step 1: Getting the `credentials.json`
This is the **most important step**. The scraper needs this file to save data to your Google Sheets.

### 1.1 Create a Project
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project dropdown (top left) and select **New Project**.
3.  Name it "Maps Scraper" and click **Create**.

### 1.2 Enable APIs
1.  In the search bar at the top, type `Google Sheets API` and select it.
2.  Click **Enable**.
3.  Search for `Google Drive API` (required for file permissions) and select it.
4.  Click **Enable**.

### 1.3 Create Credentials
1.  Go to **APIs & Services > Credentials**.
2.  Click **+ CREATE CREDENTIALS** -> **Service Account**.
3.  Name it `scraper-bot` and click **Create and Continue**.
4.  (Optional) Skip role assignment (click Done).
5.  You will see your new service account in the list (`scraper-bot@...`).
6.  **Click on the pencil icon** (Edit) or the email address.
7.  Go to the **KEYS** tab.
8.  Click **ADD KEY** -> **Create new key**.
9.  Select **JSON** and click **CREATE**.
10. A file will download to your computer. **Rename this file to `credentials.json`**.

### 1.4 Share your Sheet
1.  Open this `credentials.json` file with Notepad.
2.  Look for the `"client_email"` line (e.g., `scraper-bot@maps-scraper-123.iam.gserviceaccount.com`).
3.  Copy that email address.
4.  Go to your **Google Sheet** (where you want the leads to appear).
5.  Click the green **Share** button in the top right.
6.  **Paste the email** and ensure it has "Editor" permissions.
7.  Click **Send**.

✅ **Done!** Your scraper is now authorized to edit that sheet.

---

## 📂 Step 2: Folder Setup

Create a new folder on your Desktop named `Scraper`. Inside it, place these 3 items:
1.  **`GoogleMapsScraper.exe`** (The app).
2.  **`credentials.json`** (The key you just created).
3.  **`input.txt`** (Create a text file with your search queries).

**Example `input.txt`:**
```text
Plumbers in New York
Coffee Shops in London
Dentists in Paris
```

---

## 🚀 Step 3: First Run

1.  Double-click `GoogleMapsScraper.exe`.
2.  (First time only) Go to the **Advanced Tab** and click **Re-Install Browsers**.
    -   *Why?* The app needs a specific version of Chromium to automate the scraping. It sends a small download request to get it.
3.  Go back to the **General Tab**.
4.  Verify that "Credentials JSON" and "Input Queries File" paths are correct (Auto-detected if they are in the same folder).
5.  Click **START SCRAPING**.

---

## ❓ FAQ

**Q: The app opens then closes immediately.**
A: It likely crashed. Open a command prompt in that folder and run `GoogleMapsScraper.exe` manually to see the error message. Usually, it's missing `credentials.json`.

**Q: "Browsers not found"?**
A: Use the **Re-Install Browsers** button in the Advanced tab.

**Q: Can I use it without Google Sheets?**
A: Yes! It always saves a local `.csv` file in the `GMaps Data` folder created next to the exe.
