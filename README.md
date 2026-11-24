<div align="center">
<img width="259" height="258" alt="fetch-studio" src="https://github.com/user-attachments/assets/63d856ae-3821-467d-ac69-3565f11b20f2" />
</div>

# Fetch Studio

**Design your terminal's system-info screen (neofetch / fastfetch style) by connecting boxes. No code, no config files.**

Fetch Studio is a desktop app (PyQt6) where you build the look of your terminal greeting on a node graph and watch a
1:1 live terminal preview update as you go. When you press **Build**, it installs a small standalone script and hooks it into
your shell. After that the app can be closed: every new terminal shows your design.

Check the [WIKI](https://github.com/bobbycomet/Fetch-Studio/wiki/Home) for controls and hotkeys

To update Fetch Studio, it was added to [Griffin Updater](https://github.com/bobbycomet/GriffinUpdater)'s app list.

---

## Why it exists

Tools like neofetch and fastfetch are loved, but customizing them means editing config files, learning ANSI color codes and
fighting alignment by hand. Most people just want to say *"show my OS and RAM, put a cool logo on the left, make it purple."*

**The philosophy is simple: making a fetch should be approachable for anyone, with no code.**

* **Everything is visual.** Pick, drag, connect, recolor. What you see in the preview is what your terminal prints.
* **Nothing to memorize.** An interactive lesson walks you from an empty canvas to an installed result and won't advance until you complete each step.
* **Start simple, grow when you want.** Presets and **Classic mode** give you plain ASCII art and readouts; gradients, animation, meters and themes are there when you want them.
* **Your design is yours to share.** A project is one zip. A custom logo is one `.fsnode` file. Neither can contain code.
* **No lock-in.** The result is an ordinary bash script plus a couple of lines in your shell config. Remove it any time.

---

## How the graph works (and how node position matters)

Every design has one **Output** node. Everything you want on screen is a node connected to Output's input port:

| Node | What it adds |
|------|--------------|
| **Logo** | Built-in ASCII, your own text file, or an image/GIF, with optional gradient and animation |
| **Custom Logo** | A logo you drew in the ASCII Designer (or imported as `.fsnode`) |
| **Title** | `user@host` line, with optional underline |
| **Info** | One readout: OS, Host, Kernel, Uptime, Packages, Shell, DE, Session, Terminal (the terminal emulator, never the file manager that launched it), CPU, GPU, Memory, Disk, Swap, Load, Battery, LocalIP, Resolution, Locale, or a **Custom** command |
| **Meter bar** *(modern)* | A colored usage bar for Memory, Disk, CPU load, Swap or Battery |
| **Divider** *(modern)* | A line (optionally labeled, optionally gradient) to separate sections |
| **Color bar** | The classic row(s) of terminal palette blocks |
| **Text** | Any line of text you type |

### Position on the canvas = order on the terminal

**The vertical position of a node decides where its line appears in the terminal.** The node that is highest on the canvas is
printed first, the next one down second, and so on. If two nodes sit at the same height, the one further left goes first.

* To **reorder** your output, drag nodes up or down. The preview updates immediately.
* The **Logo / Custom Logo** node is the exception: it always occupies the left column beside the text, so its position on the
  canvas does not matter. Only the **first** logo (by position) connected to Output is used.
* Only nodes **connected to Output** are shown. A node left unplugged is ignored, which makes it handy as a parking spot.
* **Groups** (box-select with Shift, right-click, *Group selected nodes*) are for tidying the canvas. Collapsing a group does not change the order.
* Left/right placement has no effect except as the tie-breaker above, so arrange columns however keeps your graph readable.

---

## Features

### Presets and modes
* **Classic** (neofetch-like), **Advanced** (fastfetch-like) and **Custom** (you choose everything).
* **Classic mode** (toolbar toggle, saved per project): only ASCII art and system readouts. Gradients, animation, meters and dividers are hidden and ignored at build time.
* **Color themes**: Dracula, Nord, Gruvbox, Catppuccin, Tokyo Night. One click recolors the whole graph.

### Logos, gradients and animation
* Gradients: horizontal, vertical, diagonal, radial.
* Animations: rainbow, scroll, pulse, wave, typewriter, sparkle, scanline.
* Images and GIFs are converted to half-block color art. Set **Image width** (up to 200 columns) for more detail.
* **Animation lifetime** (Output node):

| Mode | Behaviour |
|------|-----------|
| `intro` (default) | Plays once when the terminal opens (about a second), then stops on the final frame. *Intro loops* can repeat it, but each loop delays your prompt. Works everywhere. |
| `live` | Keeps animating in place **until you run your first command**, then stops for good. |

  *Why not forever?* A terminal is a stream of text, not a canvas. Once text scrolls away it cannot be redrawn, and an animator
  running while a command prints would corrupt the screen. `live` needs a terminal that answers the cursor-position query and
  a Linux `/proc`, and is not guaranteed inside multiplexers or when the logo is taller than the window.

### ASCII Designer (second tab)
* Symbol palette (ASCII, box drawing, blocks and shades, geometric, arrows, symbols, braille, math). Click to pick, **drag onto the canvas**, or just type.
* Tools: Draw, Erase, Paint (per-cell color), Pick, and Select/Move for rearranging regions. Undo/redo with Ctrl+Z / Ctrl+Y.
* Starter art, text-file import, and image-to-ASCII import.
* **Save as node** adds a Custom Logo node to your graph, connected to Output, and stores it in `~/.local/share/fetchstudio/nodes/`.
  Double-click a custom node to reopen it.

### Sharing
* **Export** writes `fetchstudio(<project name>).zip` containing the node graph and every image/GIF you used. **Import** restores the graph exactly.
* **`.fsnode`** is a single-logo "plugin" file (JSON). Import validates sizes, colors and characters; plugin files are data only and can never run code. Custom logos are also embedded in the project zip.

### Build and install
**Build** writes `~/.local/share/fetchstudio/active/fetch.sh` and adds a clearly marked block to:

* `~/.bashrc` (Debian/Ubuntu, Arch, CachyOS, openSUSE, Fedora and others),
* `~/.zshrc` if you use zsh,
* `~/.config/fish/conf.d/fetchstudio.fish` if fish is installed (CachyOS ships fish by default).

**Remove** deletes the hooks and the script. The generated script is plain bash and only reads system information; the app does not need to be running.

### Saving and safety
* Auto-save every 10 minutes, **Ctrl+S** to save, and a Save / Discard / Cancel prompt when you exit or start/open/import another project with unsaved changes.
* Controls: left-drag pans, Shift+left-drag box-selects, right-click opens options (add node, group, collapse/expand, delete), scroll moves up/down, Ctrl+scroll zooms, double-click a group to collapse it.

### Interactive lesson
First launch starts a guided lesson that highlights the part of the window you need and only lets you continue when the step is done. Progress is saved; press **F1** or **Lesson** to resume or restart.

---

## Terminals

The result is printed by your shell, so it works in any terminal: GNOME Terminal, Console (`kgx`), Konsole, Xfce Terminal,
MATE Terminal, QTerminal, LXTerminal, Tilix, Deepin Terminal, COSMIC Terminal, Pantheon Terminal and others. The preview's terminal selector changes the window title and font size only.
Writing each terminal's own profile settings (fonts/palettes) is not implemented yet.

## Requirements and building

* Linux with bash, Python 3.9+ and PyQt6 (`pip install PyQt6`), then `python3 fetchstudio.py`.
* Released as an AppImage built on glibc 2.34+ by `.github/workflows/build-appimage.yml` (tag `v*` or run manually).
