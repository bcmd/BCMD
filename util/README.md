# BCMD utilities


## Syntax Highlighting

Modules are provided for highlighting the syntax of the main BCMD file formats in the following editors.

#### Gedit (Linux Distros)

Copy the files 'input.lang' to the appropriate Language directory,usually /usr/share/gtksourceview-3.0/language-specs.

For more information, visit [Gedit](https://help.gnome.org/users/gedit/stable/gedit-syntax-highlighting.html.en)

#### BBEdit/TextWrangler (Mac)

Copy the files `abcjob.plist`, `input.plist` and `modeldef.plist` to the appropriate Language Modules directory:

* BBEdit: `~/Library/Application Support/BBEdit/Language Modules`
* TextWrangler: `~/Library/Application Support/TextWrangler/Language Modules`

For more information, visit [Bare Bones Software](http://www.barebones.com/products/).


#### Notepad++ (Windows)

Import the files `batch.xml`, `input.xml` and `modeldef.xml` via the User Defined Language dialog box.

For more information, see the [Notepad++](https://notepad-plus-plus.org) home page.


## Log file parsing

(This is likely to be of interest primarily to BCMD's developers.)

Models built in DEBUG mode write a lot of information to the standard error stream. When run using the Makefile targets, this is is saved to a file in the `build` directory with the extension `.stderr`. The information contained in this file can occasionally be useful for tracking down errors in the model or the compiler, but the (lack of) structure in the log file makes it very difficult to interrogate. The script `log2csv.py` converts these files into marginally more useful tables in CSV format.