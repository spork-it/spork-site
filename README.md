# spork-site

[![Tests](https://github.com/spork-it/spork-site/actions/workflows/test.yml/badge.svg)](https://github.com/spork-it/spork-site/actions/workflows/test.yml)

Spork-native static site generation with immutable markup and structural Markdown.

## Current capabilities

Implemented and tested:

- immutable `Element`, `Fragment`, `Text`, and `RawHtml` nodes;
- recursive child and fragment flattening;
- scalar-to-text conversion and `nil` omission;
- explicit `element`, `fragment`, `text`, and `raw-html` constructors;
- locally scoped `(markup ...)` blocks with `$tag` lowering;
- normalized classes, styles, attributes, custom tags, and void elements;
- deterministic, escaped HTML serialization;
- CommonMark parsing through `markdown-it-py`;
- Markdown AST conversion into the same immutable node model;
- structural headings, paragraphs, links, images, lists, quotes, and code;
- explicit `RawHtml` nodes for Markdown inline and block HTML;
- direct composition of Markdown, authored markup, components, and sequences;
- generic immutable post-order node transformations.

Site loading and the static build pipeline are not yet implemented.

## Markup

Import the public API and the `markup` macro:

```clojure
(ns example.page
  (:require [spork-site.core :as site
             :refer [element fragment markup]]))

(defn post-card [post]
  (markup
    ($article {:class "post"}
      ($h2 (:title post))
      ($p (:summary post)))))

(defn homepage [posts]
  (markup
    ($main {:class ["content" nil]}
      ($h1 "Spork")
      (for [post posts]
        (post-card post)))))
```

`markup` only gives special meaning to lists headed by a `$`-prefixed symbol. Components, conditionals, calls, and data access remain ordinary Spork. Eager `(for ...)` expressions return persistent vectors, so generated children compose directly. Use `(doseq ...)` when iteration is only for effects.

The macro lowers to the public `element` and `fragment` bindings, so refer those names alongside `markup`. A qualified macro call also works:

```clojure
(site.markup
  ($spork-playground {:source "(+ 1 2)"}))
```

## Markdown composition

`spork-site.markdown` parses CommonMark and returns a `Fragment`, never an opaque serialized HTML string:

```clojure
(ns example.docs
  (:require
    [spork-site.core :as site :refer [markup]]
    [spork-site.markdown :as markdown]))

(def page
  {:title "Installation"
   :content (markdown.render
              "## Install\n\nRun `spork sync`.\n")
   :edit-url "/edit/install"})

(def document
  (markup
    ($article {:class "prose"}
      ($h1 (:title page))
      (:content page)
      ($a {:href (:edit-url page)} "Edit this page"))))

(site.render-html document)
```

Output:

```html
<article class="prose"><h1>Installation</h1><h2>Install</h2><p>Run <code>spork sync</code>.</p><a href="/edit/install">Edit this page</a></article>
```

The Markdown API has explicit parsing and conversion stages when plugins or AST inspection need them:

```clojure
(def ast (markdown.parse source))
(def nodes (markdown.ast-to-nodes ast))

(markdown.render source)       ; parse and convert
(markdown.render-file path)    ; UTF-8 file

; Supply a configured markdown-it parser
(def safe-parser (markdown.make-parser false)) ; disable raw HTML parsing
(markdown.render-with safe-parser source)
```

With the default parser, inline and block HTML tokens become explicit `RawHtml` nodes. Surrounding Markdown text remains `Text` and is escaped normally. `make-parser` accepts an optional boolean controlling Markdown raw HTML; it defaults to `true`.

The core facade exposes unambiguous aliases such as `site.render-markdown`, `site.parse-markdown`, and `site.markdown-ast-to-nodes`. The dedicated `spork-site.markdown` namespace is preferred when using the complete Markdown API.

## Generic transformations

`transform` walks a node tree depth-first and invokes a function post-order, after transformed children have been installed in a fresh immutable parent. The same pass therefore handles authored and Markdown-generated nodes:

```clojure
(defn heading? [node]
  (and (isinstance node site.Element)
       (contains? #{"h1" "h2" "h3" "h4" "h5" "h6"} node.tag)))

(defn mark-heading [node]
  (if (heading? node)
    (site.Element node.tag
                  (assoc node.attrs "data-heading" true)
                  node.children)
    node))

(def transformed (site.transform document mark-heading))
```

A transform may return:

- a node to retain or replace the current node;
- `nil` to remove it;
- a deterministic sequence to splice through a `Fragment`;
- a printable scalar to create a `Text` node.

Replacement nodes are not revisited during the same pass. Maps and unordered sets are rejected as markup and transformation results.

## Low-level node API

The DSL and Markdown conversion both produce the explicit API available to programs and plugins:

```clojure
(site.element :a {:class ["button" "primary"]
                  :style {:display "inline-flex" :gap "0.5rem"}
                  :href "/docs/"}
  "Read the docs")

(site.fragment
  (site.text "escaped: <tag>")
  (site.raw-html "<strong>trusted HTML</strong>"))
```

Child rules are intentionally small:

- nodes are retained;
- fragments and deterministic sequences are recursively flattened;
- strings and printable scalars become `Text` nodes;
- `nil` emits nothing;
- maps and unordered sets are rejected as children;
- `RawHtml` is the explicit escape hatch for trusted, unescaped markup.

Attributes are normalized when an element is constructed. `:class` accepts nested sequences and ignores `nil`; `:style` accepts a string or a deterministically ordered map. `nil` and `false` attributes are omitted, while `true` attributes serialize in HTML boolean form. Attribute names and output order are deterministic.

## Development

The project requires Spork 0.5.3 or later in the 0.5 line:

```bash
spork sync --dev
spork version
spork check
spork run
spork test
spork build --clean
spork dist --clean
```

`spork run` renders a small smoke-test document. The native suite covers node construction, markup lowering, normalization, escaping, CommonMark AST conversion, all primary block/inline structures, Markdown raw HTML, file rendering, mixed composition, and transformation replacement semantics.

## Project layout

```text
spork-site/
├── spork.it
├── src/spork_site/
│   ├── core.spork        # public facade and entrypoint
│   ├── markdown.spork    # CommonMark parser and AST conversion
│   ├── markup.spork      # locally scoped $tag macro
│   ├── nodes.spork       # immutable nodes and normalization
│   ├── render.spork      # deterministic HTML serialization
│   └── transforms.spork  # generic immutable tree transformations
└── tests/spork_site/
    ├── core_test.spork
    ├── markdown_test.spork
    └── transforms_test.spork
```

`spork-site.core` remains the general public facade. `spork-site.markdown` is also a supported focused namespace for Markdown integration.
