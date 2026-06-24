#!/usr/bin/env python3
from external_validation_core import main

if __name__ == "__main__":
    main(["discover", *(__import__("sys").argv[1:])])
