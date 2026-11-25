<div align="center">
<img width="259" height="258" alt="fetch-studio" src="https://github.com/user-attachments/assets/63d856ae-3821-467d-ac69-3565f11b20f2" />
</div>

# Fetch Studio

**Design your terminal's system-info screen (neofetch / fastfetch style) by connecting boxes. No code, no config files.**

Fetch Studio is a desktop app (PyQt6) where you build the look of your terminal greeting on a node graph and watch a
1:1 live terminal preview update as you go. When you press **Build**, it installs a small standalone script and hooks it into
your shell. After that the app can be closed: every new terminal shows your design.

Check the [WIKI](https://github.com/bobbycomet/Fetch-Studio/wiki/Home) for controls, hotkeys, Node reference, and how images and GIFs are handled.

To update Fetch Studio, it was added to [Griffin Updater](https://github.com/bobbycomet/GriffinUpdater)'s app list.

---

## Why it exists

Tools like neofetch and fastfetch are loved, but customizing them means editing config files, learning ANSI color codes and
fighting alignment by hand. Most people just want to say *"show my OS and RAM, put a cool logo on the left, make it purple."*

**The philosophy is simple: making a fetch should be approachable for anyone, with no code.**

* **Everything is visual.** Pick, drag, connect, recolor. What you see in the preview is what your terminal prints.
* **Nothing to memorize.** An interactive lesson walks you from an empty canvas to an installed result and won't advance until you complete each step.
* **Start simple, grow when you want.** Presets and **Classic mode** give you plain ASCII art and readouts; gradients, animation, meters and themes are there when you want them.
* **Your design is yours to share.** A project is one zip. A custom logo is one `.fsnode` file, which is data only and can never run code. A project can contain custom commands, so imports are strictly validated and commands only run after you trust them (see [Security](#security)). 
* **No lock-in.** The result is an ordinary bash script plus a couple of lines in your shell config. Remove it any time.
* **Safe by default.** Imported projects are checked before they touch the editor, and a custom shell command never runs until you have read and trusted it.

---

## How fast and acurrate is it? 

- 1:1 what you see is what you get live preview
- Once you set it up the way you want, build takes 5 seconds or less, once you hit build, it will be ready by the time you open your terminal
- Terminal opens with the system info and artwork almost immediately

---

## How the graph works (and how node position matters)

Every design has one **Output** node. Everything you want on screen is a node connected to Output's input port:

| Node | What it adds |
|------|--------------|
| **Logo** | Built-in ASCII, your own text file, or an image/GIF, with optional gradient and animation |
| **Custom Logo** | A logo you drew in the ASCII Designer (or imported as `.fsnode`) |
| **Title** | `user@host` line, with optional underline |
| **Info** | One readout: OS, Host, Kernel, Uptime, Packages, Shell, DE, Session, Terminal (the terminal emulator, never the file manager that launched it), CPU, GPU, Memory, Disk, Swap, Load, Battery, LocalIP, Resolution, Locale, grouped readouts (Environment, Clock, Storage, Network, Hardware, Services), or a **Custom** command (trust required) |
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
* Images and GIFs are converted to half-block color art. Set **Image width** (up to 200 columns) for more detail. You can now, as of 1.3.0 use kitty, iterm, and sixel for better image quality.
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

### Properties inspector
Select a node and its settings appear in tabs on the right (for an Info node: **Readout**, **Items**, **Colors**; for Output: **Layout**, **Colors**, **Animation**; and so on). Fetch Studio remembers the tab you were on for each node type, so moving between nodes keeps you where you were.

### Sharing
* **Export** writes `fetchstudio(<project name>).zip` containing the node graph and every image/GIF you used. **Import** validates it and restores the graph.
* **`.fsnode`** is a single-logo "plugin" file (JSON). Import validates sizes, colors and characters; plugin files are data only and can never run code. Custom logos are also embedded in the project zip.
* A **project** is not data only: its Info nodes can hold custom commands. See [Security](#security).

### Build and install
**Build** writes `~/.local/share/fetchstudio/active/fetch.sh` and adds a clearly marked block to:

* `~/.bashrc` (Debian/Ubuntu, Arch, CachyOS, openSUSE, Fedora and others),
* `~/.zshrc` if you use zsh,
* `~/.config/fish/conf.d/fetchstudio.fish` if fish is installed (CachyOS ships fish by default).

**Remove** deletes the hooks and the script. The generated script is plain bash; it reads system information and runs only the custom commands you trusted. The app does not need to be running.

### Calendar and the `cal` helper
The Clock readout's **Calendar** item needs the `cal` command. If it is missing, the Info node's **Items** tab offers **Install cal…**, which opens **Settings**. With the optional polkit helper, Fetch Studio installs it through `pkexec` (administrator password prompt) using the distribution's own package manager; without it, the app shows the right command for your distribution:

| Distribution | Command |
|---|---|
| Ubuntu, Debian, Linux Mint, Pop!_OS | `sudo apt update && sudo apt install ncal` |
| Fedora, RHEL, CentOS, AlmaLinux, Rocky Linux | `sudo dnf install util-linux` (`yum` on older releases) |
| Arch Linux, Manjaro, EndeavourOS | `sudo pacman -S util-linux` |
| openSUSE Tumbleweed and Leap | `sudo zypper install util-linux` |

Everything is opt-in and lives in **Settings** (toolbar):

1. **Set up helper…** asks for confirmation, then for your administrator password once (polkit). It installs a small root-owned helper that can do only two things: install `cal` and remove it again.
2. Once the helper is installed, **Install cal** appears (if `cal` is missing), plus **Remove helper**, and **Uninstall cal** when it applies.
3. **Uninstall cal** is only offered on Debian-family systems (where `cal` is its own package, `ncal`) and only if Fetch Studio installed it. On Fedora, Arch and openSUSE `cal` is part of `util-linux`, a core package that is never removed.
4. If you do not see the install cal button, your system already has it installed.

Without `pkexec`, Settings shows the command for your distribution instead. The helper is written by the app itself through `pkexec`, so nothing has to be unpacked or run by hand. Prefer the command line? `./FetchStudio-x86_64.AppImage --extract-helper` copies the files and `sudo sh install-helper.sh` installs them (`--uninstall` removes them).

## Security

A terminal greeting runs every time you open a terminal, so Fetch Studio treats anything that can execute as something you must approve.

* **`.fsnode` logo nodes are data only.** They are validated and can never run code.
* **Projects can contain custom commands.** On import (and when opening a project) Fetch Studio lists every custom command and keeps them disabled until you trust them. An imported project never trusts anything by itself.
* **Commands do not run in the preview or in a build until trusted.** Trust is per exact command text and stored only on your computer. Editing a command makes it untrusted again, so half-typed text never executes.
* **Build asks again.** Building a project with custom commands shows them and offers *Trust and build*, *Build without them* or *Cancel*.
* **Never elevated.** Commands using `sudo`, `su`, `doas`, `pkexec` or similar are blocked, and the generated script never adds any. Each command runs as your user in its own `bash -c`, with a 5 second limit and no input, so a typo cannot break your shell startup.
* **Imports are validated before use.** Node types, parameters (ranges, colors, choices), graph connections, duplicate IDs, project and asset sizes, ZIP entry names and decompressed sizes are checked. Anything unexpected is rejected with a message and nothing is written.

See the [Security wiki page](https://github.com/bobbycomet/Fetch-Studio/wiki/Security) for the full list of limits.

## Requirements and building

* Linux with bash, Python 3.9+ and PyQt6 (`pip install PyQt6`), then `python3 run.py` (or `python3 -m fetchstudio`).
* Released as an AppImage (version 2.0.0). `.github/workflows/build-appimage.yml` (tag `v*` or run manually) runs the tests, builds on glibc 2.35 and reports the glibc the bundle needs and fails if it exceeds 2.35 (the build host's version; the AppImage runs on glibc 2.35 or newer).
* Run the tests with `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests`.

### Source layout

```
run.py                     launcher / PyInstaller entry point
fetchstudio/
  common.py                imports and constants (VERSION lives here)
  specs.py readouts.py     node parameters, tabs, themes; shell snippets for every readout
  system.py security.py    helpers; custom-command trust boundary
  validation.py            project / ZIP validation
  logos.py model.py        .fsnode logos; graph model
  render.py graphics.py    colors, animation, images; kitty / iTerm2 / sixel
  compiler.py build.py     graph -> rows; standalone script and shell hooks
  caltool.py helper/       cal detection, polkit helper (script, policy, installer)
  widgets.py graphitems.py inspector.py designer.py lesson.py mainwindow.py   user interface
tests/                     unit tests
```
