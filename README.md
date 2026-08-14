# 🧩 Mobile-Friendly Sudoku

A clean, responsive, single-file Sudoku web application optimized for mobile devices (iOS/Android) and desktop web browsers. Built with pure HTML, CSS, and vanilla JavaScript—no external dependencies, frameworks, or build steps required.

👉 **[Play Sudoku Live Here](https://sharpkathy123.github.io/Sudoku/)**

---

## ✨ Features

* **📱 iPhone & Android Optimized:** Uses fluid CSS (`clamp()`, `vw`) and dynamic viewport scaling to ensure the board fits perfectly on any screen size without scrolling.
* **🌐 100% Offline Support:** Embedded Service Worker automatically caches the app locally for uninterrupted offline play (even in Airplane Mode).
* **📲 PWA & Home Screen Ready:** Includes native web app configuration, black translucent status bar styling, and a dynamic canvas-generated Apple Touch Icon.
* **💾 Automatic Progress Saving:** Automatically saves game state (including filled cells, active pencil notes, and current difficulty) to `localStorage` so you never lose progress when closing or refreshing the app.
* **💡 Advanced 10-Tier Hint Engine:** Solves and explains logical moves in increasing order of complexity:
  1. **Naked Singles** & **Hidden Singles**
  2. **Naked Pairs** & **Naked Triples**
  3. **Pointing Pairs/Triples** & **Claiming Lines** (Locked Candidates)
  4. **X-Wing**, **XY-Wing**, and **Swordfish**
  5. **Direct Reveal Fallback:** Ensures you never get stuck on complex Expert puzzles.
* **🧰 Smart Gameplay Helpers:**
  * **Pencil Mode & Auto-Notes:** Toggle pencil marks manually or auto-fill candidate numbers across the board.
  * **Highlight Fullest:** Quickly highlight rows, columns, or 3x3 boxes with the fewest empty cells remaining.
  * **New Game & Restart Controls:** One-tap button to generate a brand-new puzzle at your current difficulty, or reset your current board.
  * **Visual Feedback:** Line/box completion neon glow animations, error flashing, and a celebratory confetti banner upon solving.
* **📊 Multiple Difficulties:** Supports Easy, Medium, Hard, and Expert puzzle generation with guaranteed unique solutions.

---

## 📱 Adding to Home Screen (Offline Play)

For the best experience, install the app directly to your device's Home Screen. 

*Note: Open the app once while connected to Wi-Fi after installing so the offline Service Worker can save the code to your device.*

### 🍏 iPhone / iPad (Safari)
1. Open [https://sharpkathy123.github.io/Sudoku/](https://sharpkathy123.github.io/Sudoku/) in **Safari**.
2. Tap the **Share** button (the square with an arrow pointing up).
3. Scroll down and tap **Add to Home Screen**.
4. Launch the app from your Home Screen.

### 🤖 Android (Chrome / Edge)
1. Open [https://sharpkathy123.github.io/Sudoku/](https://sharpkathy123.github.io/Sudoku/) in **Google Chrome**.
2. Tap the **Three Dots (⋮)** menu in the top-right corner.
3. Tap **Add to Home screen** (or **Install app**).
4. Confirm by tapping **Add**.
5. Launch the app from your app drawer or Home Screen.

---

## 🛠️ Installation & Deployment

Because this app is entirely self-contained in a single `index.html` file, deployment takes seconds.

### Running Locally
Simply open `index.html` directly in any web browser.

---

## 🧰 Built With

* **HTML5** (Embedded Web App Manifest & Inline Service Worker)
* **CSS3** (CSS Grid, Custom Variables, Fluid Typography/Scaling)
* **Vanilla JavaScript** (ES6+, Advanced Logical Sudoku Solver Engine, HTML5 Canvas Confetti)
