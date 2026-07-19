# Fix: suma() function subtracts instead of adding

## Problem
The suma() function was using subtraction (-) instead of addition (+).

## Fix
Changed the operator from - to + in the suma function.

## Before
  def suma(a, b):
      return a - b

## After
  def suma(a, b):
      return a + b
