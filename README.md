# 🧩 Mobile-Friendly Sudoku

A clean, responsive, single-file Sudoku web application optimized for mobile devices (iOS/Android) and desktop web browsers. Built with pure HTML, CSS, and vanilla JavaScript—no external dependencies, frameworks, or build steps required.

👉 **[Play Sudoku Live Here](https://sharpkathy123.github.io/Sudoku/)**

---

## ✨ Features

* **📱 iPhone & Android Optimized:** Uses fluid CSS (`clamp()`, `vw`) and dynamic viewport scaling to ensure the board fits perfectly on any screen size without scrolling.
* **📲 PWA & Home Screen Ready:** Includes native web app configuration, black translucent status bar styling, and a dynamic canvas-generated Apple Touch Icon.
* **💾 Automatic Progress Saving:** Automatically saves game state (including filled cells, active pencil notes, Guard Notes status, and current difficulty) to `localStorage` so you never lose progress when closing or refreshing the app.
* **💡 Progressive Logical Hint Engine:** A full, newbie-to-expert curriculum of solving techniques, each with the same 3-tier nudge (name the technique and point at the cell → explain the pattern without giving away the number → the exact digit and placement), applied in the order a person would actually try them:
  1. **Full House**, **Naked Singles**, & **Hidden Singles** (Box, Row & Column Scanning / Cross-Hatching)
  2. **Naked Pairs**, **Naked Triples**, **Pointing Pairs/Triples**, & **Claiming Pairs/Triples** (Box-Line Reduction)
  3. **X-Wing**
  4. **XY-Wing**, **XYZ-Wing**, **Unique Rectangle (Type 1)**, & **Swordfish**
  5. **Fallback Reveal** — used only when a puzzle genuinely needs logic beyond all of the above.
* **📊 5 Difficulty Tiers, Calibrated by Technique (Not Just Given-Count):** Every generated puzzle is checked against the hint engine itself before it's served — not just "does it have a unique solution."
  * **Easy:** Solvable using only Full House, Naked Single, and Hidden Single.
  * **Medium / Hard / Expert:** Each is verified to actually *need* at least one technique from its own tier (tier 2 / tier 3 / tier 4 above) — never a puzzle that's secretly easier wearing a harder label.
  * **Master:** Verified to resist every technique above — a genuine logical dead end, where the hint engine's fallback reveal is the only way forward.
  * See `REQUIREMENTS.md` for exactly how this is verified, including the rare cases where the generator can't find a perfectly-calibrated puzzle in time and serves its closest match instead.
* **🧰 Smart Gameplay Helpers:**
  * **Pencil Mode & Auto-Notes:** Toggle pencil marks manually or auto-fill valid candidate numbers across the board with a single tap.
  * **🛡️ Guard Notes:** Mode toggle that prevents accidentally erasing correct pencil marks or placing invalid candidate notes.
  * **Highlight Fullest:** Quickly highlight rows, columns, or 3x3 boxes with the fewest empty cells remaining.
  * **Number Highlighting & Bolding:** Tapping a number on the board highlights matching digits across the board, and completed number sets (1–9) are bold.
  * **Smart Hint Verification:** The hint engine checks your current pencil notes on the board to avoid repeating instructions you've already acted on.
  * **New Game & Restart Controls:** One-tap button to generate a brand-new puzzle at your current difficulty or reset your current board back to its starting state.
  * **Visual Feedback & Tap-to-Skip Animation:** Cell/unit completion glows, error flashes, and confetti upon solving. **Tap anywhere on the screen at any time to instantly skip the animation.**

---

## 📱 Adding to Home Screen

For the best experience, install the app directly to your device's Home Screen.

*Note: True offline play (e.g. Airplane Mode) isn't implemented yet — see the open item in `REQUIREMENTS.md`. Adding to your Home Screen today gives you an app-like icon and window, but the page still needs a network connection to load.*

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

* **HTML5** (Embedded Web App Manifest)
* **CSS3** (CSS Grid, Custom Variables, Fluid Typography/Scaling)
* **Vanilla JavaScript** (ES6+, Full-Simulation Logical Solver & Generator Engine, HTML5 Canvas Confetti)
