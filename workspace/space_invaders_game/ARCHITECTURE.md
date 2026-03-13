# Architecture

## Overview
The architecture of the Space Invaders React Game will follow the Clean Architecture and Domain Driven Design principles to ensure separation of concerns and maintainability.

## Bounded Contexts
- **GameContext**: Contains all domain logic related to the game, including player, invaders, and bullets.
- **UIContext**: Contains components and logic related to the user interface.

## Layered Architecture

### 1. **Entity Layer**
- Contains domain entities, value objects, and aggregates.

### 2. **Use Case Layer**
- Contains use cases that represent the domain logic.

### 3. **Entity Service Layer**
- Contains services that interact with the database or other infrastructure.

### 4. **UI Layer**
- Contains React components and their logic.

### 5. **Framework Integration Layer**
- Contains adapters that integrate with frameworks and libraries, such as React and Axios.

## Infrastructure
- **Database**: PostgreSQL for storing game data.
- **APIs**: Axios for making HTTP requests.

## Development Approach
- **Library-First Approach**: Use existing libraries instead of writing custom code where possible.
- **Clean Architecture & DDD Principles**: Keep business logic separate from UI components and infrastructure concerns.