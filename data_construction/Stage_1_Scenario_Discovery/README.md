# Stage 1: Scenario Discovery

Languages: [English](README.md) | [中文](README.zh.md)

Stage 1 discovers real-business scenarios that can support self-evolution evaluation. Public benchmark sources such as GDPval, SOP-Bench, and JobBench provide the seed examples. A scenario agent groups related examples into candidate business scenarios and records the domain, business focus, source examples, shared entities, workflows, hidden rules, and evaluation signals.

The output is a set of scenario records. Each record should explain why its examples belong to one business world and why that world can later be expanded into a task group with related train tasks and held-out test tasks.
