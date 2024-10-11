[![CI](https://img.shields.io/github/actions/workflow/status/suhendiandigo/composify/ci.yaml?branch=main&logo=github&label=CI)](https://github.com/suhendiandigo/composify/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![license](https://img.shields.io/github/license/suhendiandigo/composify.svg)](https://github.com/suhendiandigo/composify/blob/main/LICENSE)


!!! warning  "🚧 Work in Progress" 
    This page is a work in progress.

**Composify** is a Python framework designed to simplify the development of applications. By using **rule declarations** and **dependency injection**, Composify enables clean and maintainable application structures.

Components and their relationships are declared upfront via the `@rule` decorator. The framework automatically builds a dependency graph and instantiates only the necessary components at runtime, handling dependency injection for you.

## Key Features

- **Declarative Rules**: Define components and their dependencies through a simple python function and the `@rule` decorator.
- **Dependency Injection**: Optionally use `Injector` to decorate a function and automatically auto-wire its dependencies.
- **Automated Component Creation**: Dynamically resolve dependencies and create only the required components using `GetOrCreate`.
- **Asyncio Supports**: Supports for async `@rule` via `AsyncComposify` main class.
- **Extensible**: Easily integrates with other Python libraries and frameworks with the `@rule` decorator.

## Use-cases

- **Application bootstrapping**: Write rules using `@rule` and implement custom providers as necessary to facilitate the bootstrapping of applications.
- **Dynamic rule creation**: Usable but currently **not recommended**, as the core logic has yet to be fully optimized.

## Simple Example

In this example, `Composify` automatically creates an instance of `B` by resolving its dependency on `A`, and it also shows how to auto-wire a function using the `Injector` class.

```python
from composify import Composify, rule, collect_rules
from dataclasses import dataclass


class A(int):
    pass


@dataclass(frozen=True)
class B:
    value: int


@rule
def default_a() -> A:
    return A(5)


@rule
def create_b(a: A) -> B:
    return B(a * 2)


composify = Composify(rules=collect_rules())

b = composify.get_or_create(B)
print(b)
#> B(value=10)

def custom_b(a: A) -> B:
    return B(a * 3)

# Auto-wire custom_b function.
b = composify.inject(custom_b)()
print(b)
#> B(value=15)
```

## Planned features
- **Static code generator**: Resolve dependencies at build time and generate Python code for faster bootstrapping. This would eliminate the overhead of dynamic resolution.
- **Optimization for core logic**: Reimplement the core resolver in a more efficient language, such as Rust, to improve performance.
