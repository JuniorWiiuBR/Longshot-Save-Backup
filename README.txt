===============================================================================
                              LINK'S TOOLBOX
          Mod loader + save editor for Zelda: Ocarina of Time (Triforce)
                              by Cum_Dumpster
===============================================================================

Link's Toolbox is a small Windows app for people who play Ocarina of Time
through Triforce. In one window it lets you:

  * turn your mods on and off before you play, and choose which one wins
    when two mods change the same file
  * edit your save: hearts, magic, rupees, items, ammo, bottles, keys and
    story progress, with the names the game itself uses
  * point it at a different game, mods or saves folder
  * make it look the way you like (themes and tab colours)

Nothing to install. It brings its own Python, and it never changes the game
itself. It only touches your mods folder and your save files.


-------------------------------------------------------------------------------
 GETTING STARTED
-------------------------------------------------------------------------------

  1. Unzip the "Link Toolbox" folder anywhere (Desktop, Documents, ...).
  2. Double-click  Link Toolbox.bat

The first time, the toolbox looks for your game where Triforce installed it.
If it can't find it, it asks once: pick the folder that has Triforce.exe
and the "romfs" folder in it. You can change it later in the Folders tab.

The first time you open the save editor, it reads the item and flag names
from your game files. That takes a little while, but only once.

Needs Windows 10 or 11 and a game built with Triforce.


-------------------------------------------------------------------------------
 THE MODS THAT COME WITH IT
-------------------------------------------------------------------------------

The "mods" folder in this zip has five mods:

  Young Link Mirror Shield     young Link holds the Mirror Shield in his hand
  Young Link Hylian Shield     young Link holds the Hylian Shield in his hand,
                               like the Deku Shield
  Young Link All Items         young Link can pick the adult's items in the
                               menu (big swords, Mirror Shield, hookshot...)
  Biggoron One-Handed          the Biggoron Sword swung with one hand
  Young Link Adult Motions     young Link gets the adult's motions for the big
                               swords, hookshot, bow and hammer

To install them:
  1. Open the toolbox, go to the Mods tab, click "Add mods..." and answer Yes.
  2. Press Save. (That also builds the "~Size Table" for YOUR game.)
  3. Start the game (or press Save and play).

They need the same game version they were made for: The Legend of Zelda:
Ocarina of Time v131072, built with Triforce. On another version
they may crash or not work. Turn them off in the Mods tab at any time.
Tip: give young Link the Master Sword or Biggoron Sword in the save editor's
Inventory tab to try them.


-------------------------------------------------------------------------------
 THE TABS
-------------------------------------------------------------------------------

 MODS
   Lists every mod in the game's "mods" folder.
     - Tick a mod (or press Space) to turn it on or off.
     - Up / Down sets the order. When two mods replace the same file, the
       LOWER one in the list wins. Clashes are shown in red.
     - Save writes your choice. Save and play writes it and starts the game.
     - Add mods... copies mods in: the ones that came with the toolbox, or
       any folder you pick (a mod is a folder with a "romfs" folder inside).
     - Triforce needs one shared "size table" for mods that make game files
       bigger. The toolbox builds it for you (the "~Size Table" folder) every
       time you press Save. Don't delete or edit it by hand.
   Close the game first: mods can't be switched while it is running.

 SAVE EDITOR
   Pick a save slot at the top. The summary shows hearts, rupees and
   Gold Skulltula tokens, and the Stats tab shows the picture the game
   took when you last saved.

   Stats
     Heart containers and current hearts (in quarter hearts), the magic meter
     (none / single / double) and current magic, wallet and rupees, bag and
     quiver sizes, ammo and other counts (sticks, nuts, seeds, bombs,
     bombchus, arrows, beans, scrub seeds, skulltula tokens, heart pieces),
     the five bottles and their contents, and small keys for every dungeon.
     Quick buttons: Full hearts, Full magic, Full wallet, Fill all, All keys.

   Inventory
     All 104 items by their in-game names, with their group (Swords, Shields,
     Clothes, Masks, Gear, Magic, Quest, Trade, Upgrades, Ammo) and the age
     that normally uses them.
       - Give / Take away, or double-click an item.
       - Ctrl-click or Shift-click to pick several at once.
       - "Give everything missing" fills your inventory in one go.
       - Items you have equipped, and the default clothes, can't be taken away.

   Progress
     More than 6,000 on/off story flags (events and cutscenes, talks and
     Navi hints, dungeons, places, items found, mini-games...), searchable and
     filtered by group and by On / Off / Edited. Set on / Set off works on
     several at once. Careful: some quests depend on several flags together.

   All entries
     Every value in the slot's files (progress, file-select summary, options,
     account) for advanced editing. Double-click a value to change it.

   Every list can be sorted: click a column heading, click again to reverse.
   Edited values show in red until you save.

 FOLDERS
   Use a different game folder, mods folder or saves folder. Leave a box
   empty to use the default. (Triforce only loads mods from the "mods" folder
   next to Triforce.exe.)

 LOOK
   Choose a theme (Dark green, Dark grey, Dark blue, Midnight purple, Light),
   an accent colour, and a colour for every tab. Changes show at once and
   are remembered.


-------------------------------------------------------------------------------
 SAFETY
-------------------------------------------------------------------------------

  * CLOSE THE GAME BEFORE SAVING A SAVE. A running game writes over the save
    files when it saves, and your edits would be lost.
  * Every time you save, the old files are first copied into
    app\backups\<date and time>\ . The "Backups folder" button opens it.
    To undo a save, copy the files from there back into your save folder.
  * "Undo all edits" throws away everything you changed since the last save.
  * Hearts, magic and rupees are also written to the slot's caption.sav,
    so the file-select screen shows the same numbers.


-------------------------------------------------------------------------------
 QUESTIONS
-------------------------------------------------------------------------------

 Where are my saves?
   In the game folder, under  user\save\<long number>\slot_00 ... slot_05
   (slot_00 is Slot 1).

 I edited my save but nothing changed in the game.
   The game was probably still running and wrote over the save. Close it,
   open the toolbox again, make the edit, press Save, then start the game.

 A mod doesn't show up in the game.
   Check it is ticked in the Mods tab and that you pressed Save. Mods must be
   inside the "mods" folder next to Triforce.exe, each in its own folder with
   a "romfs" folder inside. Cheat (.txt) and code mods are not supported by
   Triforce. The Notes column says when a mod isn't a RomFS mod.

 The game won't start after turning on a mod.
   Turn mods off one by one in the Mods tab (press Save each time) to find
   the one causing it.

 Can I move the toolbox folder?
   Yes. Move the whole "Link Toolbox" folder anywhere. Your settings and
   backups go with it (in the app folder).


-------------------------------------------------------------------------------
 WHAT'S INSIDE
-------------------------------------------------------------------------------

  Link Toolbox.bat     starts the toolbox
  README.txt           this file
  app\                 the toolbox itself
     toolbox.pyw         the main window
     mod_loader.pyw      Mods tab (also opens on its own)
     save_editor.pyw     Save editor tab (also opens on its own)
     nxsave.py           reads and writes the save files
     oot_catalog.py      the item list and where each value is kept
     size_table.py       builds the size table for mods
     theme.py            the colours
     jpeg_win.py         shows the slot picture (uses Windows' own decoder)
  mods\                the five mods above (install with Mods tab > Add mods...)
  python\              the Python the toolbox runs with (no install needed)

  Made by the toolbox: app\backups (save backups), app\names-cache.json
  (the names read from your game), app\toolbox_settings.json (your folders
  and colours).


-------------------------------------------------------------------------------
 CREDITS
-------------------------------------------------------------------------------

  Link's Toolbox by Cum_Dumpster.
  Built for the Triforce PC port of Ocarina of Time.
  Python is included under its own license (python\LICENSE.txt).

  This is a fan-made tool, not affiliated with Nintendo. You need your own
  copy of the game. Always keep a backup of saves you care about.

===============================================================================
