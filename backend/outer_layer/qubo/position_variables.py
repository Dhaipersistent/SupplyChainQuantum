from dataclasses import dataclass


@dataclass(frozen=True)
class PositionVariables:
    warehouses: tuple[str, ...]
    customers: tuple[str, ...]
    positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.warehouses or not self.customers or not self.positions:
            raise ValueError("Warehouses, customers, and positions must be non-empty")
        if len(set(self.warehouses)) != len(self.warehouses):
            raise ValueError("Warehouse IDs must be unique")
        if len(set(self.customers)) != len(self.customers):
            raise ValueError("Customer IDs must be unique")

    @property
    def names(self) -> tuple[tuple[str, str, int], ...]:
        return tuple(
            (warehouse, customer, position)
            for warehouse in self.warehouses
            for customer in self.customers
            for position in self.positions
        )

    @property
    def count(self) -> int:
        return len(self.warehouses) * len(self.customers) * len(self.positions)

    def index(self, warehouse: str, customer: str, position: int) -> int:
        try:
            return self.names.index((warehouse, customer, position))
        except ValueError as error:
            raise KeyError((warehouse, customer, position)) from error
