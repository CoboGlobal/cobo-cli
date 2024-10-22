import os

import pytest

from cobo_cli.utils import common


def test_is_response_success():
    assert common.is_response_success({"success": True}) == True
    assert common.is_response_success({"success": False}) == False


def test_download_file(mocker, tmp_path):
    # Mock the requests.get call
    mock_response = mocker.Mock()
    mock_response.iter_content.return_value = [b"test content"]
    mock_get = mocker.patch("requests.get", return_value=mock_response)

    # Mock open function
    mock_open = mocker.patch("builtins.open", mocker.mock_open())

    # Use a temporary directory for the test
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Call the function
    result = common.download_file("http://test.com/file.txt", str(test_dir))

    # Assertions
    assert result == str(test_dir / "file.txt")
    mock_get.assert_called_once_with(
        "http://test.com/file.txt", stream=True, timeout=10
    )
    mock_open.assert_called_once_with(str(test_dir / "file.txt"), "wb")
    mock_open().write.assert_called_once_with(b"test content")


def test_extract_file(tmp_path):
    # Create a test zip file and verify extraction
    import zipfile

    test_zip = tmp_path / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("test.txt", "test content")

    extract_dir = tmp_path / "extract"
    common.extract_file(str(test_zip), str(extract_dir))

    assert (extract_dir / "test.txt").read_text() == "test content"
