from cobo_cli.utils.app import download_file, extract_file
from cobo_cli.utils.authorization import is_response_success


def test_is_response_success():
    assert is_response_success({"success": True})
    assert not is_response_success({"success": False})


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
    download_file("http://test.com/file.txt", str(test_dir / "file.txt"))

    # Assertions ?
    # assert result == str(test_dir / "file.txt")
    mock_get.assert_called_once_with("http://test.com/file.txt", stream=True)
    mock_open.assert_called_once_with(str(test_dir / "file.txt"), "wb")
    mock_open().write.assert_called_once_with(b"test content")


def test_extract_file(tmp_path):
    # Create a test tar.gz file and verify extraction
    import os
    import tarfile

    # 创建测试目录和文件
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("test content")

    # 创建 tar.gz 文件
    test_archive = tmp_path / "test.tar.gz"
    with tarfile.open(test_archive, "w:gz") as tar:
        # 将文件添加到归档中，使用相对路径
        tar.add(test_file, arcname="test.txt")

    # 确保归档文件被正确创建
    assert os.path.exists(test_archive)

    # 创建提取目录
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # 提取文件
    extract_file(str(test_archive), str(extract_dir))

    # 验证提取结果
    extracted_file = extract_dir / "test.txt"
    assert extracted_file.exists()
    assert extracted_file.read_text() == "test content"

    # 清理
    test_archive.unlink()
