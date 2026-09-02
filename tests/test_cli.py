from typer.testing import CliRunner
from aidbg.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI Black Box Debugger" in result.stdout


def test_cli_init_and_config():
    result = runner.invoke(app, ["init", "--service", "test-svc"])
    assert result.exit_code == 0
    assert "Initialized AIBD configuration" in result.stdout

    cfg_result = runner.invoke(app, ["config"])
    assert cfg_result.exit_code == 0
    assert "test-svc" in cfg_result.stdout
