# Composify

[![CI](https://img.shields.io/github/actions/workflow/status/suhendiandigo/composify/ci.yaml?branch=main&logo=github&label=CI)](https://github.com/suhendiandigo/composify/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![license](https://img.shields.io/github/license/suhendiandigo/composify.svg)](https://github.com/suhendiandigo/composify/blob/main/LICENSE)

**Composify** is a Python framework designed to simplify the development of **declarative applications**. By using **rule declarations** and **dependency injection**, Composify enables clean, maintainable, and scalable application architectures.

Components and their relationships are declared upfront via the `@rule` decorator. The framework automatically builds a dependency graph and instantiates only the necessary components at runtime, handling dependency injection for you.

## Key Features

- **Declarative Rules**: Define components and their dependencies through a simple python function and `@rule` declarator.
- **Dependency Injection**: Using `Injector`, wraps a function and automatically inject its dependencies.
- **Automated Component Creation**: Dynamically resolve dependencies and create only the required components.
- **Scalability**: Suitable for both small and large-scale applications.
- **Extensible**: Easily integrates with other Python libraries and frameworks by creating using the `@rule` decorator.

## Simple Example

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
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

