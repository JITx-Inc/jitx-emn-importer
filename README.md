# jitx-emn-importer



## How to use:

Run the following command in your JITX project:

```
$> $SLM add -git JITx-Inc/jitx-emn-importer
```

This will add a line like this to your `slm.toml` file:

```
[dependencies]
jitx-emn-importer = { git = "JITx-Inc/jitx-emn-importer", version = "0.1.0" }
```

## Usage in Code
In order to generate the JITX code that mirrors the data in the EMN file, at the REPL (i.e. JITX shell) you need to call the `import-emn` function to generate a `board.stanza` file.

```
import-emn(<path/to/input_emn_file>, <resulting_package_name>, <path/to/output/stanza_file>)
```
e.g.
```
stanza> import-emn("hello.emn", "my-package", "board.stanza")
```

Inside this `board.stanza` file, two variables/functions are created. The first is a variable that contains the geometry of the board outline.

`public val emn-board-outline`

Use this variable as your `boundary` parameter in `pcb-board` definition in your existing project. For example,

```
pcb-board my-board :
  boundary = emn-board-outline
  ...
```
The other object in the `board.stanza` file defines all of the other imported mechanical data on the board such as cutouts, text, etc. In order to use this data in your board, you need to define a separate module that imports the definition from the `board.stanza` file as follows.

`public defn emn-module ()`

This function should be called inside of a `pcb-module` at your top level  and set it to location `loc(0.0, 0.0)`. For example,

```
public pcb-module my-emn-cutouts :
  emn-module()

pubilc pcb-module my-top-level-module :
  inst cutouts : my-emn-cutouts
  place(cutouts) at loc(0.0, 0.0) on Top
  ...
```

