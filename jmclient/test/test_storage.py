from __future__ import print_function, absolute_import, division, unicode_literals

from jmclient import storage
import pytest


class MockStorage(storage.Storage):
    def __init__(self, data, *args, **kwargs):
        self.file_data = data
        self.locked = False
        super(type(self), self).__init__(*args, **kwargs)

    def _read_file(self):
        if hasattr(self, 'file_data'):
            return self.file_data
        return b''

    def _write_file(self, data):
        self.file_data = data

    def _create_lock(self):
        self.locked = not self.read_only

    def _remove_lock(self):
        self.locked = False


def test_storage():
    s = MockStorage(None, 'nonexistant', b'password', create=True)
    assert s.file_data.startswith(s.MAGIC_ENC)
    assert s.locked
    assert s.is_encrypted()
    assert not s.was_changed()

    old_data = s.file_data

    s.data[b'mydata'] = b'test'
    assert s.was_changed()
    s.save()
    assert s.file_data != old_data
    enc_data = s.file_data

    old_data = s.file_data
    s.change_password(b'newpass')
    assert s.is_encrypted()
    assert not s.was_changed()
    assert s.file_data != old_data

    old_data = s.file_data
    s.change_password(None)
    assert not s.is_encrypted()
    assert not s.was_changed()
    assert s.file_data != old_data
    assert s.file_data.startswith(s.MAGIC_UNENC)

    s2 = MockStorage(enc_data, __file__, b'password')
    assert s2.locked
    assert s2.is_encrypted()
    assert not s2.was_changed()
    assert s2.data[b'mydata'] == b'test'


def test_storage_invalid():
    with pytest.raises(storage.StorageError, message="File does not exist"):
        MockStorage(None, 'nonexistant', b'password')

    s = MockStorage(None, 'nonexistant', b'password', create=True)
    with pytest.raises(storage.StorageError, message="Wrong password"):
        MockStorage(s.file_data, __file__, b'wrongpass')

    with pytest.raises(storage.StorageError, message="No password"):
        MockStorage(s.file_data, __file__)

    with pytest.raises(storage.StorageError, message="Non-wallet file, unencrypted"):
        MockStorage(b'garbagefile', __file__)

    with pytest.raises(storage.StorageError, message="Non-wallet file, encrypted"):
        MockStorage(b'garbagefile', __file__, b'password')


def test_storage_readonly():
    s = MockStorage(None, 'nonexistant', b'password', create=True)
    s = MockStorage(s.file_data, __file__, b'password', read_only=True)
    s.data[b'mydata'] = b'test'

    assert not s.locked
    assert s.was_changed()

    with pytest.raises(storage.StorageError):
        s.save()

    with pytest.raises(storage.StorageError):
        s.change_password(b'newpass')


def test_storage_lock(tmpdir):
    p = str(tmpdir.join('test.jmdat'))
    pw = None

    with pytest.raises(storage.StorageError, message="File does not exist"):
        storage.Storage(p, pw)

    s = storage.Storage(p, pw, create=True)
    assert s.is_locked()
    assert not s.is_encrypted()
    assert s.data == {}

    with pytest.raises(storage.StorageError, message="File is locked"):
        storage.Storage(p, pw)

    assert storage.Storage.is_storage_file(p)
    assert not storage.Storage.is_encrypted_storage_file(p)

    s.data[b'test'] = b'value'
    s.save()
    s.close()
    del s

    s = storage.Storage(p, pw, read_only=True)
    assert not s.is_locked()
    assert s.data == {b'test': b'value'}
    s.close()
    del s

    s = storage.Storage(p, pw)
    assert s.is_locked()
    assert s.data == {b'test': b'value'}
