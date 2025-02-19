# jitx-emn-importer



## How to use:

Run the following command in your JITX project:

```
$> $SLM add -git JITx-Inc/jitx-emn-importer
```

This will add a line like this to your `slm.toml` file:

```
[dependencies]
mechanical = { git = "JITx-Inc/jitx-emn-importer", version = "0.1.0" }
```

## Usage in Code

Run `import-emn` to generate a board file.

```
import-emn(<path/to/input_emn_file>, <resulting_package_name>, <path/to/output/stanza_file>)
```
e.g.
```
import-emn("hello.emn", "my-package", "board.stanza")
```

Inside the board file, you will find two variable/function

`public val emn-board-outline`

put this in your `boundary` parameter in `pcb-board`. For example,

```
pcb-board my-board :
  boundary = emn-board-outline
  ...
```

`public defn emn-module ()`

put this inside your `pcb-module` and set it to location `(0.0, 0.0)`. For example,

```
public pcb-module my-cutouts :
  emn-module()

pubilc pcb-module my-module :
  inst cutouts : my-cutouts
  place(cutouts) at loc(0.0, 0.0) on Top
  ...
  ...
```

