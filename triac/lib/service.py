import importlib


class ServiceStatus:
    def __init__(
        self,
        enabled: str,
        enabled_preset: str,
        active: str,
        condition_res: bool,
        active_entered_tst: int,
        active_exit_tst : int,
        inactive_entered_tst: int,
        inactive_exit_tst: int,
        condition_tst: int,
    ) -> None:
        self.__enabled = enabled
        self.__enabled_preset = enabled_preset
        self.__active = active
        self.__condition_res = condition_res
        self.__active_entered_tst = active_entered_tst
        self.__active_exit_tst = active_exit_tst
        self.__inactive_entered_tst = inactive_entered_tst
        self.__inactive_exit_tst = inactive_exit_tst
        self.__condition_tst = condition_tst

    @property
    def enabled(self) -> str:
        """
        Possible values: "enabled", "enabled-runtime", "linked",
            "linked-runtime", "masked", "masked-runtime", "static",
            "disabled", and "invalid"

        "masked" means the unit is symlinked to /dev/null or empty
        """
        return self.__enabled

    @property
    def enabled_preset(self) -> str:
        """
        Preset which services should be enabled
        https://www.freedesktop.org/software/systemd/man/latest/systemd.preset.html

        If this is set to enabled, this is considered the same
        as specifying enabled via systemctl itself (see documentation) above
        """
        return self.__enabled_preset

    @property
    def active(self) -> str:
        """
        Possible values: "active", "reloading", "inactive", "failed",
            "activating", and "deactivating"
        """
        return self.__active

    @property
    def active_entered_tst(self) -> int:
        return self.__active_entered_tst

    @property
    def active_exit_tst(self) -> int:
        return self.__active_exit_tst
    
    @property
    def inactive_entered_tst(self) -> int:
        return self.__inactive_entered_tst

    @property
    def inactive_exit_tst(self) -> int:
        return self.__inactive_exit_tst
        
    @property
    def condition_res(self) -> bool:
        return self.__condition_res

    @property
    def condition_tst(self) -> int:
        return self.__condition_tst

    def __repr__(self) -> str:
        return ""


class ServiceStatusFetcher:

    @staticmethod
    def fetch(name: str) -> ServiceStatus:
        systemd = importlib.import_module("pystemd.systemd1")
        service = systemd.Unit(name, _autoload=True)

        # Fetch data
        enabled = service.Unit.UnitFileState.decode("utf-8")
        enabled_preset = service.Unit.UnitFilePreset.decode("utf-8")
        active = service.Unit.ActiveState.decode("utf-8")
        condition_res = service.Unit.ConditionResult

        # Timestamps
        active_entered_tst = service.Unit.ActiveEnterTimestampMonotonic
        active_exit_tst = service.Unit.ActiveExitTimestampMonotonic
        inactive_entered_tst = service.Unit.InactiveEnterTimestampMonotonic
        inactive_exit_tst = service.Unit.InactiveExitTimestampMonotonic
        condition_tst = service.Unit.ConditionTimestampMonotonic

        return ServiceStatus(
            enabled,
            enabled_preset,
            active,
            condition_res,
            active_entered_tst,
            active_exit_tst,
            inactive_entered_tst,
            inactive_exit_tst,
            condition_tst
        )
