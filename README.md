# spork-site

[![Tests](https://github.com/spork-it/spork-site/actions/workflows/test.yml/badge.svg)](https://github.com/spork-it/spork-site/actions/workflows/test.yml)

Spork-native static site generation with immutable markup, structural Markdown, and deterministic content builds.

## Capabilities

- immutable `Element`, `Fragment`, `Text`, and `RawHtml` nodes;
- locally scoped `(markup ...)` blocks with `$tag` lowering;
- deterministic, escaped HTML serialization;
- CommonMark AST conversion into the shared node model;
- YAML front matter and recursive Markdown discovery;
- eager persistent filtering, sorting, and limiting of content collections;
- generated clean routes and duplicate/conflicting output detection;
- ordinary functions for components and layouts;
- Pygments syntax highlighting over structural code nodes;
- static asset discovery and copying;
- deterministic full builds with safe output cleanup;
- a project-local `spork site ...` command provider for source-only sites;
- XML sitemap, RSS 2.0, and Atom 1.0 generation;
- generic immutable post-order node transformations.

## Content-driven site

Markdown documents use optional YAML front matter:

````markdown
---
title: First Post
date: 2026-08-30T12:00:00Z
summary: A post built with Spork.
tags: [spork, release]
---
## Hello

```python
print("Spork")
```
````

Discovering a content directory returns an eager persistent vector of document maps:

```clojure
(ns example.site
  (:require
    [spork-site.build :as build]
    [spork-site.collections :as collections]
    [spork-site.content :as content]
    [spork-site.core :as site :refer [element fragment markup]]
    [spork-site.feeds :as feeds]
    [spork-site.routing :as routing]
    [spork-site.sitemap :as sitemap]))

(def documents (content.load-documents "content"))
```

Each document contains front-matter fields at the top level plus canonical fields:

```clojure
{:source-path   #p"content/blog/first.md"
 :relative-path "blog/first.md"
 :id            "blog/first"
 :slug          "first"
 :route         "/blog/first/"
 :metadata      {:title "First Post" ...}
 :body          "## Hello\n..."
 :content       (Fragment [...])
 :title         "First Post"
 :date          #inst"2026-08-30T12:00:00Z"}
```

YAML mappings and sequences become persistent maps and vectors. YAML dates remain Python `date`/`datetime` values. Front-matter sets are rejected because they are unordered.

Routes are derived from relative paths:

| Source | Route | Output |
|---|---|---|
| `index.md` | `/` | `index.html` |
| `docs/index.md` | `/docs/` | `docs/index.html` |
| `blog/hello.md` | `/blog/hello/` | `blog/hello/index.html` |

Use `slug`, `route`, `permalink`, or `url` front matter to override the derived route. Explicit routes are validated and canonicalized.

Pass `:patterns` to select several deterministic globs, or disable highlighting when loading:

```clojure
(content.load-documents
  "content"
  * :patterns ["docs/**/*.md" "blog/**/*.md"]
    :highlight? false)
```

## Collections

Collections use ordinary Spork predicates and callable keys rather than a query language:

```clojure
(defn published? [document]
  (not (is (:draft document) true)))

(def posts
  (collections.collection
    documents
    * :where published?
      :sort-by :date
      :order :desc
      :limit 20))
```

`collection`, `filter-documents`, and `sort-documents` eagerly return persistent vectors. Standard functions such as `filter`, `group-by`, `take`, and eager `(for ...)` expressions remain available for further composition.

## Components, layouts, and generated routes

Components and layouts are ordinary functions returning node-like values:

```clojure
(defn document-layout [document]
  (markup
    ($html {:lang "en"}
      ($head
        ($meta {:charset "utf-8"})
        ($meta {:name "viewport"
                :content "width=device-width, initial-scale=1"})
        ($title (:title document))
        ($link {:rel "stylesheet" :href "/site.css"}))
      ($body
        ($main {:class "prose"}
          ($h1 (:title document))
          (:content document))))))

(def content-pages
  (routing.pages-for posts document-layout))
```

`pages-for` is equivalent to an eager generated route expression:

```clojure
(for [document posts]
  (routing.page (:route document)
                (document-layout document)))
```

`routing.page` serializes structural content as escaped HTML. Use `routing.output-file` for already serialized text or bytes such as `robots.txt`, XML, or JSON.

Duplicate canonical routes, page/asset collisions, and file/directory output conflicts fail before output is cleaned or written.

## Syntax highlighting

Fenced Markdown code gets a `language-*` class during Markdown conversion. Content loading applies Pygments by default and retains the shared structure:

```clojure
(def highlighted
  (site.highlight-syntax
    (site.render-markdown "```spork\n(+ 1 2)\n```")))
```

The result remains `Element("pre")` containing `Element("code")`; only Pygments' trusted, escaped span markup is represented as `RawHtml`. Unknown lexer names leave the original code block unchanged.

## Sitemap and feeds

Sitemap entries are any route-bearing maps. `:lastmod`, `:changefreq`, and `:priority` are optional, and `:sitemap false` excludes an entry:

```clojure
(def sitemap-output
  (sitemap.sitemap "https://example.com" posts))
```

RSS and Atom consume the same document maps. Entries require `:title`, `:route`, and one of `:updated`, `:date`, or `:published`. Drafts and entries with `:feed false` are excluded.

```clojure
(def feed-config
  {:title "Example Blog"
   :description "News from Example"
   :url "https://example.com"
   :author "Example Authors"})

(def rss-output (feeds.rss feed-config posts))
(def atom-output (feeds.atom feed-config posts))
```

Feed timestamps derive from content dates, never the wall clock, so repeated builds are byte-for-byte stable. Empty feeds require an explicit `:updated` value.

## Complete build

A site is an ordinary persistent map constructed by `build.site`:

```clojure
(defn make-site []
  (build.site
    * :output "public"
      :pages [content-pages
              (routing.output-file "/sitemap.xml" sitemap-output)
              (routing.output-file "/feed.xml" rss-output)
              (routing.output-file "/atom.xml" atom-output)]
      :assets (build.discover-assets "static")
      :transforms []))
```

The factory is an ordinary source function. Configure it independently from the application's `:main`:

```clojure
{:name "example"
 :version "0.1.0"
 :spork-version ">=0.6,<0.7"
 :dependencies ["spork-site>=0.1,<0.2"]
 :source-paths ["src"]

 :site
 {:target "example.site:make-site"
  :watch ["spork.it" "src" "content" "static"]}

 :main "example.app:main"}
```

Synchronize once, then use the project-local provider:

```bash
spork sync
spork site check
spork site routes
spork site build
spork site clean
```

`spork-site` loads `example.site:make-site` directly from configured source paths through the Spork command context. The site does not need an ahead-of-time build, a Python-importable adapter, a replacement application entry point, or manual virtualenv activation.

A build:

1. validates and canonicalizes every route;
2. detects duplicate, page/asset, and parent/child path conflicts;
3. renders all page content and transformations;
4. validates asset sources and output safety;
5. cleans the output directory by default;
6. writes pages and assets in lexical output-path order;
7. returns a persistent summary map.

```clojure
{:output #p"/project/public"
 :pages 12
 :assets 4
 :written ["atom.xml" "feed.xml" "index.html" ...]}
```

Set `:clean? false` to retain unrelated output files. Output paths cannot be the project directory, an ancestor of it, or a filesystem root. Asset sources inside a cleaned output directory are rejected before deletion.

## Site commands

The package owns one complete top-level CLI:

```text
spork site build [--output PATH] [--no-clean] [--json]
spork site check [--json]
spork site clean [--output PATH]
spork site routes [--json]
spork site version
```

`check` loads the source factory and constructs the complete rendered page, asset, conflict, and output plan without creating, cleaning, or writing the output directory. `routes` performs the same validation and reports canonical route/output pairs. `clean` uses the factory's configured output by default and applies the same project-root and filesystem-root protections as builds. `version` reports the selected provider version, Spork host version, command API, and project/active scope.

The former built-module facade remains temporarily available for compatibility:

```bash
spork run --main spork-site.cli:main build example.site:site-config public
```

It is no longer the primary project workflow.

## Markup

`markup` only gives special meaning to lists headed by a `$`-prefixed symbol. Components, conditionals, calls, data access, and iteration remain ordinary Spork:

```clojure
(defn post-card [post]
  (markup
    ($article {:class "post"}
      ($h2 ($a {:href (:route post)} (:title post)))
      ($p (:summary post)))))

(defn homepage [posts]
  (markup
    ($main {:class ["content" nil]}
      ($h1 "Spork")
      (for [post posts]
        (post-card post)))))
```

The macro lowers to public `element` and `fragment` bindings, so refer those names with `markup`. A qualified macro call also works:

```clojure
(site.markup
  ($spork-playground {:source "(+ 1 2)"}))
```

## Markdown and transformations

`spork-site.markdown` parses CommonMark into `Fragment`, `Element`, `Text`, and explicit `RawHtml` values, never an opaque HTML string:

```clojure
(def ast (site.parse-markdown source))
(def nodes (site.markdown-ast-to-nodes ast))
(def content (site.render-markdown source))
```

With the default parser, inline and block HTML tokens become explicit `RawHtml` nodes. Surrounding text remains escaped `Text`. Use `(site.make-markdown-parser false)` to disable Markdown raw HTML.

`transform` walks a node tree depth-first and invokes a function post-order after transformed children have been installed in a fresh immutable parent:

```clojure
(defn mark-heading [node]
  (if (and (isinstance node site.Element)
           (contains? #{"h1" "h2" "h3" "h4" "h5" "h6"} node.tag))
    (site.Element node.tag
                  (assoc node.attrs "data-heading" true)
                  node.children)
    node))

(def transformed (site.transform content mark-heading))
```

A transform may return a node, `nil` to remove it, a deterministic sequence to splice through a fragment, or a printable scalar to create a `Text` node.

## Low-level node API

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

Attributes are normalized during construction. `:class` accepts nested sequences and ignores `nil`; `:style` accepts a string or deterministically ordered map. `nil` and `false` attributes are omitted, while `true` attributes serialize in HTML boolean form.

## Development

The project requires Spork 0.6 in order to publish and exercise the command-provider API:

```bash
spork sync --dev
spork check
spork test
spork run version
spork build --clean
spork dist --clean
```

The test suite includes structural unit tests and an end-to-end documentation-and-blog fixture covering front matter, recursive discovery, collections, generated routes, layouts, syntax highlighting, assets, deterministic rebuilding, sitemap, RSS, and Atom.

## Project layout

```text
src/spork_site/
├── build.spork        # deterministic output planning and execution
├── cli.spork          # package-owned build/check/clean/routes/version CLI
├── collections.spork  # eager document filtering and sorting
├── content.spork      # front matter, discovery, and document loading
├── core.spork         # general public facade
├── feeds.spork        # RSS and Atom
├── highlight.spork    # structural Pygments integration
├── markdown.spork     # CommonMark AST conversion
├── markup.spork       # locally scoped $tag macro
├── nodes.spork        # immutable nodes and normalization
├── render.spork       # deterministic HTML serialization
├── routing.spork      # routes and generated pages
├── sitemap.spork      # sitemap XML
├── transforms.spork   # generic immutable tree transformations
└── xml.spork          # shared XML/date/URL helpers
```

Focused namespaces are supported APIs; `spork-site.core` re-exports the general application-facing surface.
