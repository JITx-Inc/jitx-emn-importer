# jitx-emn-importer



## How to Enable

Run the following command at the command prompt in your JITX project directory:

```
$> $SLM add -git JITx-Inc/jitx-emn-importer
```

This will add a line like this to your `slm.toml` file:

```
[dependencies]
jitx-emn-importer = { git = "JITx-Inc/jitx-emn-importer", version = "0.1.1" }
```

## Running the Importer

In order to generate the JITX code that mirrors the data in the EMN file, at the REPL (i.e. JITX shell) you need to call the `import-emn` function to generate a `board.stanza` file.  

```
import-emn(<path/to/input_emn_file>, <resulting_package_name>, <path/to/output/stanza_file>)
```
To start, you will need to restart the JITX shell in order for `slm` to download and install the repo. After restarting the shell, you will also need import the library at the command prompt e.g.
```
stanza> import emn-importer
stanza> import-emn("hello.emn", "my-package", "board.stanza")
```

## Usage in Code

In order to use this new `board.stanza` file in your project, you should add it to your project's `stanza.proj` as follows:

```
package my-package/board defined-in "board.stanza"
```
And in your top level design file you should also import this new package as follows:
```
import my-package/board
```

Inside the created `board.stanza` file, one variable and one function are present. The variable contains the board outline geometry that is accessible in the user's board definition.

`public val emn-board-outline`

Use this as your `boundary` parameter in `pcb-board` definition in your existing project. For example,

```
pcb-board my-board :
  boundary = emn-board-outline ; use the variable available in the board.stanza file
  ...
```
The module definition in the `board.stanza` file contains the other imported mechanical data from the board such as cutouts, text, etc. You can edit the module definition to change the layers and text for instance.

`public defn emn-module ()`

In order to correctly use this data in your design, you will define a new `pcb-module` that calls this function. In order to ensure correct placement, place it at location `loc(0.0, 0.0)` at the top level. For example,

```
public pcb-module my-emn-cutouts :
  emn-module() ; let's instantiate the mechanical data

pubilc pcb-module my-top-level-module :
  inst cutouts : my-emn-cutouts ; to import the data into the top level
  place(cutouts) at loc(0.0, 0.0) on Top ; now let's correctly place the imported mechanical data
  ...
```

## Using EMN (IDF/BDF) files as a Cadence user

In Cadence PCB tools, like Allegro, you have the ability to export IDF format files. Choose that option and to also filter out all objects except cutouts and board edge. If you export with the defaults, the export data will also contain all cutouts of vias, pads, etc. The resulting `.bdf` file is in the EMN format and can be used by this importer.
