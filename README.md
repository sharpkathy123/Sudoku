# 🧩 Mobile-Friendly Sudoku

A clean, responsive, single-file Sudoku web application optimized for mobile devices (iOS/Android) and desktop web browsers. Built with pure HTML, CSS, and vanilla JavaScript—no external dependencies, frameworks, or build steps required.

👉 **[Play Sudoku Live Here](https://sharpkathy123.github.io/Sudoku/)**

---

## ✨ Features

* **📱 iPhone & Android Optimized:** Uses fluid CSS (`clamp()`, `vw`) and dynamic viewport scaling to ensure the board fits perfectly on any screen size without scrolling.
* **🌐 100% Offline Support:** Embedded Service Worker automatically caches the app locally for uninterrupted offline play (even in Airplane Mode). Includes a discreet version timestamp in the header to confirm when code updates take effect.
* **📲 PWA & Home Screen Ready:** Includes native web app configuration, black translucent status bar styling, and a dynamic canvas-generated Apple Touch Icon.
* **💾 Automatic Progress Saving:** Automatically saves game state (including filled cells, active pencil notes, Guard Notes status, and current difficulty) to `localStorage` so you never lose progress when closing or refreshing the app.
* **💡 Progressive Logical Hint Engine:** Features a progressive nudge-to-full explanation system that guides you through techniques step by step:
  1. **Naked Singles** & **Hidden Singles** (Box & Line Scanning)
  2. **Naked Pairs**, **Naked Triples**, & **Pointing Pairs/Triples**
  3. **Claiming Lines** (Locked Candidates)
  4. **X-Wing**, **XY-Wing**, **XYZ-Wing**, **Swordfish**, and **Unique Rectangles (Type 1)**
* **📊 5 Difficulty Tiers with Guaranteed Quality:**
  * **Easy, Medium, and Hard:** Solvable using standard scanning, singles, pairs, and locked candidates.
  * **Expert:** Guaranteed to be 100% solvable using our built-in logical solver techniques—**zero direct-reveal hints required**.
  * **Master:** Extreme puzzles requiring advanced logic chains. If a board hits a logical bottleneck beyond standard solver patterns, the hint engine can directly reveal a cell value rather than a step-by-step rule.
* **🧰 Smart Gameplay Helpers:**
  * **Pencil Mode & Auto-Notes:** Toggle pencil marks manually or auto-fill valid candidate numbers across the board with a single tap.
  * **🛡️ Guard Notes:** Mode toggle that prevents accidentally erasing correct pencil marks or placing invalid candidate notes.
  * **Highlight Fullest:** Quickly highlight rows, columns, or 3x3 boxes with the fewest empty cells remaining.
  * **Number Highlighting & Bolding:** Tapping a number on the board highlights matching digits across the board, and completed number sets (1–9) are bold.
  * **Smart Hint Verification:** The hint engine checks your current pencil notes on the board to avoid repeating instructions you've already acted on.
  * **New Game & Restart Controls:** One-tap button to generate a brand-new puzzle at your current difficulty or reset your current board back to its starting state.
  * **Visual Feedback & Tap-to-Skip Animation:** Cell/unit completion glows, error flashes, and confetti upon solving. **Tap anywhere on the screen at any time to instantly skip the animation.**

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
* **Vanilla JavaScript** (ES6+, Full-Simulation Logical Solver & Generator Engine, HTML5 Canvas Confetti)
