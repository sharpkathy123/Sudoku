# 🧩 Mobile-Friendly Sudoku

A clean, responsive, single-file Sudoku web application optimized for mobile devices (iOS/Android) and desktop web browsers. Built with pure HTML, CSS, and vanilla JavaScript—no external dependencies, frameworks, or build steps required.

---

## ✨ Features

* **📱 iPhone & Mobile Optimized:** Uses fluid CSS (`clamp()`, `vw`) and dynamic viewport scaling to ensure the board fits perfectly on any screen size without scrolling.
* **🌐 100% Offline Support:** Embedded Service Worker automatically caches the app locally for uninterrupted offline play (even in Airplane Mode).
* **📲 iOS Home Screen Ready:** Includes native web app configuration, black translucent status bar styling, and a dynamic canvas-generated Apple Touch Icon so it installs like a native app.
* **💡 Smart Gameplay Helpers:**
  * **Pencil Mode & Auto-Notes:** Toggle pencil marks or auto-fill candidate numbers for empty cells.
  * **Highlight Least Unfilled:** Quickly highlight rows, columns, or 3x3 boxes with the fewest empty cells remaining.
  * **Logical Hint System:** Get targeted hints based on single candidates and hidden singles.
  * **Visual Feedback:** Line/box completion animations, error flashing, and a confetti celebratory banner upon solving.
* **📊 Multiple Difficulties:** Supports Easy, Medium, Hard, and Expert puzzle generation with guaranteed unique solutions.

---

## 🛠️ Installation & Deployment

Because this app is entirely self-contained in a single `index.html` file, deployment takes seconds.

### Running Locally
Simply open `index.html` directly in any web browser.

---

## 📱 Adding to iPhone Home Screen

1. Open your deployed URL in Safari on iOS.
2. Tap the **Share** button (the square with an up arrow).
3. Tap **Add to Home Screen**.
4. Launch the app directly from your Home Screen to enjoy full-screen standalone mode without browser navigation bars.

---

## 🧰 Built With

* **HTML5** (Embedded Web App Manifest & Inline Service Worker)
* **CSS3** (CSS Grid, Custom Variables, Fluid Typography/Scaling)
* **Vanilla JavaScript** (ES6+, Backtracking Puzzle Generator & Solver, HTML5 Canvas Confetti)
