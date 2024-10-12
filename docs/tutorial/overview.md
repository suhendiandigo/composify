!!! warning  "🚧 Work in Progress" 
    This page is a work in progress.


Using Composify, we are going to use a declarative approach on building applications.
We are going to write series of rules leading up to the creation for a single final object that acts as our entry point.


```python
from composify import Composify, rule, collect_rules
from dataclasses import dataclass


class Application:

    def __init__(self, hello: str):
        self.hello = hello

    def run(self):
        print(self.hello)


@dataclass(frozen=True)
class Config:
    hello_message: str


@rule
def create_app(config: Config) -> Application:
    return Application(value=config.value)


@rule
def default_config() -> Config:
    return Config(
        value="Hello, world",
    )


composify = Composify(rules=collect_rules())

application = composify.get_or_create.one(Application)

application.run()
#> Hello, world

```

The piece of code above declare the creation of an `Application` via the `create_app` rule. 
The creation of `Application` requires a single `Config` object which creation is declared via
the `default_config` rule. 

The dependency graph of the rules roughly translate to:
```mermaid
graph LR
    create_app(@create_app) --> Application
    default_config(@default_config) --> Config
    Config --> create_app
```

Using this rule set, we requested a single `Application` to `Composify` and we successfully 
created an instance of `Application` using the default configuration.
