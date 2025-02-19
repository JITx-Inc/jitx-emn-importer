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
In order to generate the JITX code that mirrors the data in the EMN file, at the REPL (i.e. JITX shell) you need to run `import-emn` to generate a `board.stanza` file.

```
import-emn(<path/to/input_emn_file>, <resulting_package_name>, <path/to/output/stanza_file>)
```
e.g.
```
import-emn("hello.emn", "my-package", "board.stanza")
```

Inside the board file, you will find two variables/functions. The first is a variable that contains the geometry of the board outline.

`public val emn-board-outline`

Put this in your `boundary` parameter in `pcb-board`. For example,

```
pcb-board my-board :
  boundary = emn-board-outline
  ...
```
The next function defines all of the other mechanical data on the board such as cutouts, text, etc.
`public defn emn-module ()`

put this object at your top level inside of a `pcb-module` and set it to location `loc(0.0, 0.0)`. For example,

```
public pcb-module my-emn-cutouts :
  emn-module()

pubilc pcb-module my-top-level-module :
  inst cutouts : my-emn-cutouts
  place(cutouts) at loc(0.0, 0.0) on Top
  ...
  ...
```

