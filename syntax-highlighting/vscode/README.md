## VSCodium/VSCode Syntax Highlighting for catsoop Files

This directory contains the source code for an extension that adds syntax
highlighting for `.catsoop` files to VSCodium/VSCode.

* First, you can either download the extension from <https://catsoop.org/_static/catsoop-syntax-0.0.2.vsix> or build it yourself by running the following commands from this directory:
    ```
    $ npm install --no-save @vscode/vsce
    $ node_modules/.bin/vsce package
    ```

* Then you can install the extension in any of three different ways:
    * By running `$ code --install-extension catsoop-syntax-0.0.2.vsix`, or
    * By opening that file under Extensions -> Install from VSIX, or
    * By dragging that file into the Extensions panel of the editor.
