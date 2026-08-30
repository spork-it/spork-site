# spork-site

Spork-native static site generation. Milestone 0 implements the immutable markup model that the generator will build on.

## Status: Milestone 0

Implemented and tested:

- immutable `Element`, `Fragment`, `Text`, and `RawHtml` nodes;
- recursive child and fragment flattening;
- scalar-to-text conversion and `nil` omission;
- explicit `element`, `fragment`, `text`, and `raw-html` constructors;
- locally scoped `(markup ...)` blocks with `$tag` lowering;
- standard and custom element names;
- normalized class vectors and deterministic style maps;
- deterministic, escaped HTML and attribute serialization;
- HTML void-element handling and markup validation.

Markdown and the static-site build pipeline begin in later milestones.

## Usage

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
      [for [post posts]
        (post-card post)])))

(site.render-html
  (homepage [{:title "Hello" :summary "Built with Spork."}]))
```

Output:

```html
<main class="content"><h1>Spork</h1><article class="post"><h2>Hello</h2><p>Built with Spork.</p></article></main>
```

`markup` only gives special meaning to lists headed by a `$`-prefixed symbol. Components, conditionals, calls, and data access remain ordinary Spork. Use Spork's vector comprehension (`[for ...]`) when a loop should produce children; statement-form `(for ...)` retains its normal side-effect-only semantics.

The macro lowers to the public `element` and `fragment` bindings, so refer those two names alongside `markup` as shown above. Keeping the expansion on ordinary public bindings makes source execution and ahead-of-time builds produce the same node classes.

A qualified macro call works too:

```clojure
(site.markup
  ($spork-playground {:source "(+ 1 2)"}))
```

## Low-level node API

The DSL lowers to the same explicit API available to programs and plugins:

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

```bash
spork sync --dev
spork check
spork run
spork test
spork build --clean
```

`spork run` renders a small smoke-test document. The native test suite covers structural nodes, immutability, normalization, escaping, raw HTML, custom and void elements, macro lowering, components, conditionals, comprehensions, and the milestone north-star page.

## Project layout

```text
spork-site/
├── spork.it
├── src/spork_site/
│   ├── core.spork       # public facade and entrypoint
│   ├── markup.spork     # locally scoped $tag macro
│   ├── nodes.spork      # immutable nodes and normalization
│   └── render.spork     # deterministic HTML serialization
└── tests/spork_site/core_test.spork
```

`spork-site.core` remains the public facade, so consumers do not depend on the internal module boundaries.
