# ruff: noqa: N801
from mersal.configuration.dependency_resolver import DependencyResolver

__all__ = (
    "DepA",
    "DepB",
    "DepC",
    "Dep_C_Decorated",
    "Dep_C_Decorated_A_ThirdTime",
    "Dep_C_Decorated_Again",
    "TestDependencyResolver",
)


class DepA:
    pass


class DepB:
    def __init__(self, dep_a: DepA) -> None:
        self.dep_a = dep_a


class DepC:
    pass


class Dep_C_Decorated:
    def __init__(self, dep_c: DepC) -> None:
        self.dep_c = dep_c


class Dep_C_Decorated_Again:
    def __init__(self, dep_c: DepC) -> None:
        self.dep_c = dep_c


class Dep_C_Decorated_A_ThirdTime:
    def __init__(self, dep_c: DepC, dep_a: DepA) -> None:
        self.dep_c = dep_c
        self.dep_a = dep_a


class TestDependencyResolver:
    def test_basic_resolve(self):
        subject = DependencyResolver()
        dep_a_instance = DepA()
        subject.register(DepA, lambda x: dep_a_instance)

        assert subject[DepA] is dep_a_instance

    def test_basic_resolve_should_return_same_instance(self):
        subject = DependencyResolver()
        subject.register(DepA, lambda x: DepA())

        first_instance = subject[DepA]
        second_instance = subject[DepA]
        assert first_instance is second_instance

    def test_resolve_when_one_dependency_depends_on_other(self):
        subject = DependencyResolver()
        subject.register(DepB, lambda d: DepB(dep_a=d[DepA]))
        dep_a_instance = DepA()
        subject.register(DepA, lambda d: dep_a_instance)

        dep_b = subject[DepB]
        assert dep_b
        assert dep_b.dep_a is dep_a_instance

    def test_basic_decoration(self):
        subject = DependencyResolver()
        dep_c = DepC()
        subject.register(DepC, lambda d: dep_c)
        subject.decorate(DepC, lambda d: Dep_C_Decorated(d[DepC]))

        dep_c_decorated = subject[DepC]
        assert isinstance(dep_c_decorated, Dep_C_Decorated)

    def test_applies_decoration_in_correct_order(self):
        subject = DependencyResolver()
        dep_c = DepC()
        subject.register(DepC, lambda d: dep_c)
        subject.decorate(DepC, lambda d: Dep_C_Decorated(d[DepC]))
        subject.decorate(DepC, lambda d: Dep_C_Decorated_Again(d[DepC]))

        dep_c_decorated = subject[DepC]
        assert isinstance(dep_c_decorated, Dep_C_Decorated_Again)

    def test_decorator_with_other_deps(self):
        subject = DependencyResolver()
        dep_a = DepA()
        dep_c = DepC()

        subject.register(DepA, lambda d: dep_a)
        subject.register(DepC, lambda d: dep_c)
        subject.decorate(DepC, lambda d: Dep_C_Decorated(d[DepC]))
        subject.decorate(DepC, lambda d: Dep_C_Decorated_Again(d[DepC]))
        subject.decorate(DepC, lambda d: Dep_C_Decorated_A_ThirdTime(d[DepC], d[DepA]))

        dep_c_decorated = subject[DepC]
        assert isinstance(dep_c_decorated.dep_a, DepA)  # pyright: ignore[reportAttributeAccessIssue]

    def test_dependency_that_depends_on_itself(self):
        class DepFoo:
            def __init__(self):
                self.count = 0

        class DepFooDecorator:
            def __init__(self, dep: DepFoo):
                self.dep = dep

            @property
            def count(self):
                return self.dep.count + 1

        foo = DepFoo()
        subject = DependencyResolver()
        subject.register(DepFoo, lambda _: foo)
        subject.decorate(DepFoo, lambda d: DepFooDecorator(d[DepFoo]))
        subject.decorate(DepFoo, lambda d: DepFooDecorator(d[DepFoo]))
        assert subject[DepFoo].count == 2
