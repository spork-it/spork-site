# spork-site

[![Tests](https://github.com/spork-it/spork-site/actions/workflows/test.yml/badge.svg)](https://github.com/spork-it/spork-site/actions/workflows/test.yml)

Spork-native static publishing with immutable markup, structural CommonMark, deterministic output plans, and isolated full-rebuild development serving.

## Add it to a project

Configure the package and a source factory in `spork.it`:

```clojure
{:name "example-site"
 :version "0.1.0"
 :spork-version ">=0.6,<0.7"
 :dependencies ["spork-site>=0.1,<0.2"]
 :source-paths ["src"]
 :site {:target "example-site.site:make-site"
        :watch ["spork.it" "src" "content" "static"]}}
```

A site factory is an ordinary Spork source function:

```clojure
(ns example-site.site
  (:require
    [spork-site.build :as build]
    [spork-site.core :refer [element fragment markup]]
    [spork-site.routing :as routing]))

(defn home []
  (markup
    ($html {:lang "en"}
      ($head ($meta {:charset "utf-8"}) ($title "Example"))
      ($body ($main ($h1 "Hello"))))))

(defn make-site []
  (build.site
    * :output "public"
      :pages [(routing.page "/" (home))]
      :assets (build.discover-assets "static")))
```

Synchronize once, then use the package-owned command:

```bash
spork sync
spork site check
spork site routes
spork site serve --open
spork site build
```

Sites do not need an ahead-of-time Python build, an adapter executable, or an application `:main`.

## Contracts

- Markup and Markdown share immutable `Element`, `Fragment`, `Text`, and explicit `RawHtml` nodes.
- Content, routes, feeds, sitemaps, assets, and output order are deterministic.
- Unsafe output arrangements and route or target conflicts fail before deletion or writing.
- `check` validates the complete rendered plan without modifying output.
- Development serving activates only complete successful generations and retains the last success after failures.
- Reload code is injected into served HTML only, never generated files.

## Documentation

The complete reference is maintained on `spork.sh`:

- [Package overview](https://spork.sh/docs/packages/spork-site/)
- [Getting started](https://spork.sh/docs/packages/spork-site/getting-started/)
- [Content and collections](https://spork.sh/docs/packages/spork-site/content/)
- [Routing and layouts](https://spork.sh/docs/packages/spork-site/routing-and-layouts/)
- [Builds and commands](https://spork.sh/docs/packages/spork-site/builds-and-commands/)
- [Development server](https://spork.sh/docs/packages/spork-site/development-server/)
- [Markup](https://spork.sh/docs/packages/spork-site/markup/)
- [Markdown and transforms](https://spork.sh/docs/packages/spork-site/markdown-and-transforms/)
- [Node API](https://spork.sh/docs/packages/spork-site/node-api/)

This website is the canonical production consumer; its source remains an ordinary source-only Spork project.

## Development

```bash
spork sync --dev
spork check
spork test
spork build --clean
spork dist --clean
```

## License

[MIT](LICENSE)
