
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
ESXi guest VM console client.
"""

import os
import re
import ssl
import sys
import time
import datetime
import urllib.request
import urllib.parse


try:
    from pyVim.connect import SmartConnect, Disconnect  # type: ignore
    from pyVmomi import vim  # type: ignore

    HAS_PYVMOMI = True
except Exception:  # pragma: no cover - import-time capability flag
    SmartConnect = None  # type: ignore
    Disconnect = None  # type: ignore
    vim = None  # type: ignore
    HAS_PYVMOMI = False


MOD_NONE = 0x00
MOD_LSHIFT = 0x02
HID_CAPSLOCK = 0x39


SPECIAL_KEYS = {
    "ENTER": 0x28,
    "ESC": 0x29,
    "BACKSPACE": 0x2A,
    "TAB": 0x2B,
    "SPACE": 0x2C,
    "F1": 0x3A,
    "F2": 0x3B,
    "F3": 0x3C,
    "F4": 0x3D,
    "F5": 0x3E,
    "F6": 0x3F,
    "F7": 0x40,
    "F8": 0x41,
    "F9": 0x42,
    "F10": 0x43,
    "F11": 0x44,
    "F12": 0x45,
    "INSERT": 0x49,
    "HOME": 0x4A,
    "PAGEUP": 0x4B,
    "DELETE": 0x4C,
    "END": 0x4D,
    "PAGEDOWN": 0x4E,
    "RIGHT": 0x4F,
    "LEFT": 0x50,
    "DOWN": 0x51,
    "UP": 0x52,
    "NUMPAD_SLASH": 0x54,
    "NUMPAD_STAR": 0x55,
    "NUMPAD_MINUS": 0x56,
    "NUMPAD_PLUS": 0x57,
    "NUMPAD_ENTER": 0x58,
    "NUMPAD_1": 0x59,
    "NUMPAD_2": 0x5A,
    "NUMPAD_3": 0x5B,
    "NUMPAD_4": 0x5C,
    "NUMPAD_5": 0x5D,
    "NUMPAD_6": 0x5E,
    "NUMPAD_7": 0x5F,
    "NUMPAD_8": 0x60,
    "NUMPAD_9": 0x61,
    "NUMPAD_0": 0x62,
    "NUMPAD_DOT": 0x63,
}


CHAR_MAP = {
    # Numbers and punctuations
    '1': (0x1E, MOD_NONE),  '!': (0x1E, MOD_LSHIFT),
    '2': (0x1F, MOD_NONE),  '@': (0x1F, MOD_LSHIFT),
    '3': (0x20, MOD_NONE),  '#': (0x20, MOD_LSHIFT),
    '4': (0x21, MOD_NONE),  '$': (0x21, MOD_LSHIFT),
    '5': (0x22, MOD_NONE),  '%': (0x22, MOD_LSHIFT),
    '6': (0x23, MOD_NONE),  '^': (0x23, MOD_LSHIFT),
    '7': (0x24, MOD_NONE),  '&': (0x24, MOD_LSHIFT),
    '8': (0x25, MOD_NONE),  '*': (0x25, MOD_LSHIFT),
    '9': (0x26, MOD_NONE),  '(': (0x26, MOD_LSHIFT),
    '0': (0x27, MOD_NONE),  ')': (0x27, MOD_LSHIFT),
    # Letters
    'a': (0x04, MOD_NONE),  'A': (0x04, MOD_LSHIFT),
    'b': (0x05, MOD_NONE),  'B': (0x05, MOD_LSHIFT),
    'c': (0x06, MOD_NONE),  'C': (0x06, MOD_LSHIFT),
    'd': (0x07, MOD_NONE),  'D': (0x07, MOD_LSHIFT),
    'e': (0x08, MOD_NONE),  'E': (0x08, MOD_LSHIFT),
    'f': (0x09, MOD_NONE),  'F': (0x09, MOD_LSHIFT),
    'g': (0x0A, MOD_NONE),  'G': (0x0A, MOD_LSHIFT),
    'h': (0x0B, MOD_NONE),  'H': (0x0B, MOD_LSHIFT),
    'i': (0x0C, MOD_NONE),  'I': (0x0C, MOD_LSHIFT),
    'j': (0x0D, MOD_NONE),  'J': (0x0D, MOD_LSHIFT),
    'k': (0x0E, MOD_NONE),  'K': (0x0E, MOD_LSHIFT),
    'l': (0x0F, MOD_NONE),  'L': (0x0F, MOD_LSHIFT),
    'm': (0x10, MOD_NONE),  'M': (0x10, MOD_LSHIFT),
    'n': (0x11, MOD_NONE),  'N': (0x11, MOD_LSHIFT),
    'o': (0x12, MOD_NONE),  'O': (0x12, MOD_LSHIFT),
    'p': (0x13, MOD_NONE),  'P': (0x13, MOD_LSHIFT),
    'q': (0x14, MOD_NONE),  'Q': (0x14, MOD_LSHIFT),
    'r': (0x15, MOD_NONE),  'R': (0x15, MOD_LSHIFT),
    's': (0x16, MOD_NONE),  'S': (0x16, MOD_LSHIFT),
    't': (0x17, MOD_NONE),  'T': (0x17, MOD_LSHIFT),
    'u': (0x18, MOD_NONE),  'U': (0x18, MOD_LSHIFT),
    'v': (0x19, MOD_NONE),  'V': (0x19, MOD_LSHIFT),
    'w': (0x1A, MOD_NONE),  'W': (0x1A, MOD_LSHIFT),
    'x': (0x1B, MOD_NONE),  'X': (0x1B, MOD_LSHIFT),
    'y': (0x1C, MOD_NONE),  'Y': (0x1C, MOD_LSHIFT),
    'z': (0x1D, MOD_NONE),  'Z': (0x1D, MOD_LSHIFT),
    # More punctuations and space
    '-':  (0x2D, MOD_NONE),  '_':  (0x2D, MOD_LSHIFT),
    '=':  (0x2E, MOD_NONE),  '+':  (0x2E, MOD_LSHIFT),
    '[':  (0x2F, MOD_NONE),  '{':  (0x2F, MOD_LSHIFT),
    ']':  (0x30, MOD_NONE),  '}':  (0x30, MOD_LSHIFT),
    '\\': (0x31, MOD_NONE),  '|':  (0x31, MOD_LSHIFT),
    ';':  (0x33, MOD_NONE),  ':':  (0x33, MOD_LSHIFT),
    "'":  (0x34, MOD_NONE),  '"':  (0x34, MOD_LSHIFT),
    '`':  (0x35, MOD_NONE),  '~':  (0x35, MOD_LSHIFT),
    ',':  (0x36, MOD_NONE),  '<':  (0x36, MOD_LSHIFT),
    '.':  (0x37, MOD_NONE),  '>':  (0x37, MOD_LSHIFT),
    '/':  (0x38, MOD_NONE),  '?':  (0x38, MOD_LSHIFT),
    ' ':  (0x2C, MOD_NONE),
    # None printables
    '\n': (0x28, MOD_NONE),
    '\r': (0x28, MOD_NONE),
    '\t': (0x2B, MOD_NONE),
    '\b': (0x2A, MOD_NONE),
}


def _hostname_name_matches(actual, wanted):
    if not actual or not wanted:
        return False
    a, w = actual.lower(), wanted.lower()
    if a == w:
        return True
    return a.split(".")[0] == w.split(".")[0]


def _find_datacenter(content, name):
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datacenter], True
    )
    try:
        for dc in container.view:
            if dc.name == name:
                return dc
    finally:
        container.Destroy()
    raise RuntimeError("Datacenter not found: {0!r}".format(name))


def _find_vm(content, name, datacenter=None, esxi_hostname=None):
    if datacenter:
        dc = _find_datacenter(content, datacenter)
        root = dc.vmFolder
    else:
        root = content.rootFolder

    container = content.viewManager.CreateContainerView(
        root, [vim.VirtualMachine], True
    )
    matches = []
    try:
        for vm in container.view:
            if vm.name != name:
                continue
            if esxi_hostname:
                hostname = vm.runtime.host
                if hostname is None:
                    continue
                if not _hostname_name_matches(hostname.name, esxi_hostname):
                    continue
            matches.append(vm)
    finally:
        container.Destroy()

    if not matches:
        msg = "VM not found: {0!r}".format(name)
        if datacenter:
            msg += " (datacenter={0!r})".format(datacenter)
        if esxi_hostname:
            msg += " (esxi_hostname={0!r})".format(esxi_hostname)
        raise RuntimeError(msg)
    
    if len(matches) > 1:
        hostnames = []
        for vm in matches:
            h = vm.runtime.host
            hostnames.append(h.name if h else "?")
        raise RuntimeError(
            "Multiple VMs named {0!r} after filtering: host {1!r}".format(
                name, hostnames
            )
        )
    return matches[0]


def _make_modifier_type(modifiers):
    if isinstance(modifiers, vim.vm.UsbScanCodeSpec.ModifierType):
        return modifiers
    mod = vim.vm.UsbScanCodeSpec.ModifierType()
    mod.leftControl = bool(modifiers & 0x01)
    mod.leftShift = bool(modifiers & 0x02)
    mod.leftAlt = bool(modifiers & 0x04)
    mod.leftGui = bool(modifiers & 0x08)
    mod.rightControl = bool(modifiers & 0x10)
    mod.rightShift = bool(modifiers & 0x20)
    mod.rightAlt = bool(modifiers & 0x40)
    mod.rightGui = bool(modifiers & 0x80)
    return mod


def _press_key(vm, hid_code, modifiers=0):
    spec = vim.vm.UsbScanCodeSpec()
    down = vim.vm.UsbScanCodeSpec.KeyEvent()
    down.usbHidCode = (hid_code << 16) | 0x07
    if modifiers:
        down.modifiers = _make_modifier_type(modifiers)
    up = vim.vm.UsbScanCodeSpec.KeyEvent()
    up.usbHidCode = 0
    spec.keyEvents = [down, up]
    return vm.PutUsbScanCodes(spec)


def _parse_datastore_path(result):
    if result is None:
        return None
    if isinstance(result, str):
        return result
    if hasattr(result, "screenshotFile"):
        return result.screenshotFile
    if hasattr(result, "fileName"):
        return result.fileName
    if hasattr(result, "path"):
        return result.path
    return None


def _get_vm_datacenter(vm):
    current = getattr(vm, "parent", None)
    while current is not None:
        if isinstance(current, vim.Datacenter):
            return current
        current = getattr(current, "parent", None)
    return None


def _normalize_datastore_url(url, hostname):
    if not url:
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "*" and hostname:
        return urllib.parse.urlunparse(parsed._replace(netloc=hostname))
    return url


def _build_datastore_file_url(datastore_path, datacenter_obj, hostname):
    if not isinstance(datastore_path, str):
        return None
    match = re.match(r"^\s*\[([^\]]+)\]\s*(.+)$", datastore_path)
    if not match:
        return None

    datastore_name = match.group(1)
    file_path = match.group(2).lstrip("/")
    if not file_path:
        return None

    if not hostname or hostname == "*":
        return None
    if datacenter_obj is None or not getattr(datacenter_obj, "name", None):
        return None

    encoded_path = urllib.parse.quote(file_path, safe="/")
    encoded_dc = urllib.parse.quote(datacenter_obj.name, safe="")
    encoded_ds = urllib.parse.quote(datastore_name, safe="")
    return "https://{hostname}/folder/{path}?dcPath={dc}&dsName={ds}".format(
        hostname=hostname, path=encoded_path, dc=encoded_dc, ds=encoded_ds
    )


def _download_datastore_file(
    si,
    content,
    datacenter_obj,
    datastore_path,
    out_path,
    validate_certs=True
):
    download_url = None
    transfer_method = getattr(
        content.fileManager,
        "InitiateFileTransferFromDatastore", None
    )
    if transfer_method is not None:
        fti = content.fileManager.InitiateFileTransferFromDatastore(
            datacenter=datacenter_obj, datastorePath=datastore_path
        )
        download_url = getattr(fti, "url", None)
        if not download_url:
            raise RuntimeError("Unable to obtain datastore transfer URL")
    elif isinstance(datastore_path, str) and datastore_path.startswith(
        ("http://", "https://")
    ):
        download_url = datastore_path
    else:
        stub = getattr(si, "_stub", None)
        hostname = None
        if stub is not None:
            hostname = getattr(stub, "hostname", None)
            if not hostname:
                uri = getattr(stub, "uri", None)
                if uri:
                    parsed_uri = urllib.parse.urlparse(uri)
                    hostname = parsed_uri.netloc

        download_url = _build_datastore_file_url(datastore_path, datacenter_obj, hostname)
        if download_url is None:
            raise RuntimeError(
                "Unable to download datastore file: neither FileManager.InitiateFileTransferFromDatastore nor datastore URL build is available. "
                "datastore_path={0!r}".format(datastore_path)
            )

    stub = getattr(si, "_stub", None)
    hostname = None
    if stub is not None:
        hostname = getattr(stub, "hostname", None)
        if not hostname:
            uri = getattr(stub, "uri", None)
            if uri:
                parsed_uri = urllib.parse.urlparse(uri)
                hostname = parsed_uri.netloc

    download_url = _normalize_datastore_url(download_url, hostname)
    if not download_url:
        raise RuntimeError("download_url is empty after normalization")
    if not isinstance(download_url, str):
        raise RuntimeError("download_url must be a string")
    
    headers = {}
    cookie = getattr(stub, "cookie", None)
    if cookie:
        headers["Cookie"] = cookie

    ctx = None
    if not validate_certs:
        ctx = ssl._create_unverified_context()

    request = urllib.request.Request(download_url, headers=headers)
    with urllib.request.urlopen(request, context=ctx) as response:
        data = response.read()

    with open(out_path, "wb") as out_file:
        out_file.write(data)


def _delete_datastore_file(content, datacenter_obj, datastore_path, timeout=60):
    task = content.fileManager.DeleteDatastoreFile_Task(
        name=datastore_path, datacenter=datacenter_obj
    )
    deadline = time.monotonic() + timeout
    while task.info.state not in ("success", "error"):
        if time.monotonic() > deadline:
            raise RuntimeError(
                "Timed out waiting for datastore file deletion after {0}s".format(timeout)
            )
        time.sleep(1.0)
    if task.info.state != "success":
        raise RuntimeError(
            "Unable to delete datastore file: {0}".format(task.info.error)
        )


class VMKeyboard(object):
    """
    Simple keyboard sender using PutUsbScanCodes.

    By default, emulates the ESXi 7.0.3-safe behavior:
      - Uppercase letters via CapsLock toggling.
      - Shifted punctuation and symbols are sent using the shift modifier so all
        mapped CHAR_MAP keys are exercised during testing.
    """

    def __init__(self, vm, sleep_time=0.05):
        self.vm = vm
        self.sleep_time = sleep_time
        self.caps_on = False

    def _set_caps(self, wanted):
        if self.caps_on != wanted:
            _press_key(self.vm, HID_CAPSLOCK)
            time.sleep(0.1)
            self.caps_on = wanted

    def reset_caps(self):
        _press_key(self.vm, HID_CAPSLOCK)
        time.sleep(0.1)
        _press_key(self.vm, HID_CAPSLOCK)
        time.sleep(0.1)
        self.caps_on = False

    def special(self, key_name):
        key_name = key_name.upper()
        if key_name not in SPECIAL_KEYS:
            raise ValueError(
                "Unknown special key: {0!r}. Valid: {1}".format(
                    key_name, sorted(SPECIAL_KEYS.keys())
                )
            )
        _press_key(self.vm, SPECIAL_KEYS[key_name])
        time.sleep(self.sleep_time)

    def type(self, text):
        skipped = []
        for ch in text:

            if ch not in CHAR_MAP:
                skipped.append(ch)
                continue
            
            hid, mod = CHAR_MAP[ch]

            if mod == MOD_LSHIFT and ch.isalpha():
                self._set_caps(True)
                _press_key(self.vm, hid)
            elif mod == MOD_LSHIFT:
                self._set_caps(False)
                _press_key(self.vm, hid, modifiers=MOD_LSHIFT)
            else:
                self._set_caps(False)
                _press_key(self.vm, hid)
            
            time.sleep(self.sleep_time)
        
        self._set_caps(False)
        return skipped

    def type_line(self, text):
        skipped = self.type(text)
        if text and not text.endswith("\n"):
            self.special("ENTER")
        return skipped


def _connect_vsphere(hostname, username, password, port=443, validate_certs=True):
    if validate_certs:
        si = SmartConnect(
            hostname=hostname,
            username=username,
            pwd=password,
            port=port
        )
    else:
        ctx = ssl._create_unverified_context()
        si = SmartConnect(
            hostname=hostname,
            username=username,
            pwd=password,
            port=port,
            sslContext=ctx
        )
    return si


def _screenshot(
    si,
    content,
    vm,
    name,
    datacenter,
    keep_screenshot=False,
    validate_certs=True,
):
    try:
        print("Requesting VM screenshot via CreateScreenshot_Task()...")
        task = vm.CreateScreenshot_Task()
        deadline = time.monotonic() + 60
        while task.info.state not in ("success", "error"):
            if time.monotonic() > deadline:
                print("Timed out waiting for screenshot task after 60s", file=sys.stderr)
                return
            time.sleep(1.0)

        if task.info.state != "success":
            print("Screenshot task failed:", task.info.error)
            return

        datastore_path = _parse_datastore_path(task.info.result)
        print("Screenshot task completed successfully.")
        if not datastore_path:
            print(
                "Screenshot task succeeded but no datastore path was returned "
                "(task.info.result={0!r})".format(task.info.result)
            )
            return

        if datacenter:
            dc = _find_datacenter(content, datacenter)
        else:
            dc = _get_vm_datacenter(vm)

        if dc is None:
            print(
                "Could not resolve datacenter for VM; cannot download screenshot. "
                "Datastore path was: {0}".format(datastore_path),
                file=sys.stderr,
            )
            return
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_file = os.path.join(
            os.getcwd(),
            "{0}-console-test-{1}.png".format(name, ts),
        )

        print("Downloading screenshot to:", out_file)
        _download_datastore_file(
            si=si,
            content=content,
            datacenter_obj=dc,
            datastore_path=datastore_path,
            out_path=out_file,
            validate_certs=validate_certs,
        )
        if not keep_screenshot:
            print("Deleting screenshot from datastore: {0}".format(datastore_path))
            try:
                _delete_datastore_file(
                    content=content,
                    datacenter_obj=dc,
                    datastore_path=datastore_path,
                )
            except Exception as e:
                print(
                    "Warning: failed to delete datastore screenshot: {0}".format(e),
                    file=sys.stderr,
                )
        else:
            print("Leaving screenshot in datastore as requested.")
    except Exception as e:  # pragma: no cover - depends on vSphere backing
        print("Failed to create screenshot:", e, file=sys.stderr)


def esxi_vm_console(
    hostname,
    username,
    password,
    name,
    commands,
    datacenter="ha-datacenter",
    esxi_hostname=None,
    port=443,
    sleep_time=0.1,
    validate_certs=True,
    screenshot=False,
    keep_screenshot=False,
    dry_run=False,
):
    if not HAS_PYVMOMI:
        print("pyVmomi is required for this tester", file=sys.stderr)
        return 1

    print(
        "Connecting to {hostname} as {username}, vm={vm}".format(
            hostname=hostname, username=username, vm=name
        )
    )
    si = None
    try:
        si = _connect_vsphere(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            validate_certs=validate_certs,
        )
        content = si.RetrieveContent()
        vm = _find_vm(
            content,
            name,
            datacenter=datacenter,
            esxi_hostname=esxi_hostname,
        )

        print("Connected. VM runtime host:", getattr(vm.runtime.host, "name", "?"))

        if dry_run:
            line_chars = [ch for ch in sorted(CHAR_MAP.keys())
                if ch not in ("\n", "\t", "\b")]
            print("Dry run. Characters that would be sent in one line:")
            print("".join(line_chars))
            print(
                "Special keys to be sent: {0}".format(
                    ", ".join(sorted(SPECIAL_KEYS.keys()))
                )
            )
            return 0

        kb = VMKeyboard(vm, sleep_time=sleep_time)
        kb.reset_caps()

        all_skipped = []
        for command, wait in commands or []:
            print(f"Sending command to VM console: {command}")
            skipped = kb.type_line(command)
            all_skipped.extend(skipped)
            if wait is not None:
                time.sleep(wait)

            if screenshot:
                _screenshot(
                    si=si,
                    content=content,
                    vm=vm,
                    name=name,
                    datacenter=datacenter,
                    keep_screenshot=keep_screenshot,
                    validate_certs=validate_certs,
                )

        if all_skipped:
            uniq = sorted(set(all_skipped))
            print(
                "WARNING: {n} character occurrences were skipped: {chars}".format(
                    n=len(all_skipped), chars=", ".join(uniq)
                )
            )

        return 0
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 1
    finally:
        if si is not None and Disconnect is not None:
            try:
                Disconnect(si)
            except Exception:
                pass

if __name__ == "__main__":
    import argparse

    class StringOrPair(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            current = getattr(namespace, self.dest, None) or []
            if isinstance(values, list):
                if len(values) == 1:
                    current.append((values[0], None))
                else:
                    current.append((values[0], float(values[1])))
            else:
                current.append((values, None))
            setattr(namespace, self.dest, current)

    class CustomHelpFormatter(argparse.HelpFormatter):
        def _format_action_invocation(self, action):
            if not action.option_strings:
                # Positional argument
                (metavar,) = self._metavar_formatter(action, action.dest)(1)
                return metavar
            else:
                parts = []
                # if Optional doesn't take a value, format is: -s, --long
                if action.nargs == 0:
                    parts.extend(action.option_strings)
                # if Optional takes a value, format is: -s ARGS, --long=ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        if option_string.startswith("--"):
                            parts.append("%s=%s" % (option_string, args_string))
                        else:
                            parts.append("%s %s" % (option_string, args_string))
                return ", ".join(parts)

    parser = argparse.ArgumentParser(
        description="Send commands to a VMware guest console.",
        add_help=False,
        formatter_class=CustomHelpFormatter,
    )

    mandatory = parser.add_argument_group("Mandatory arguments")
    optional = parser.add_argument_group("Optional arguments")

    # Add mandatory arguments
    mandatory.add_argument(
        "--hostname",
        required=True,
        help="vCenter or ESXi hostname/IP"
    )
    mandatory.add_argument(
        "--username",
        required=True,
        help="vCenter or ESXi username"
    )
    mandatory.add_argument(
        "--password",
        required=True,
        help="vCenter or ESXi password"
    )
    mandatory.add_argument(
        "--name",
        required=True,
        help="Virtual Machine name"
    )
    mandatory.add_argument(
        "--command",
        nargs='+',
        required=True,
        dest="commands",
        action=StringOrPair,
        help="Command to send to guest console, optionally followed by wait time in seconds,\
              or multiple --command arguments each with their own command and optional wait time"
    )
    
    # Add optional arguments
    optional.add_argument(
        "-h", "--help",
        action="help",
        help="show this help message and exit"
    )
    optional.add_argument(
        "--datacenter",
        default="ha-datacenter",
        help="Datacenter name (default 'ha-datacenter')"
    )
    optional.add_argument(
        "--esxi-hostname",
        default=None,
        help="Require VM to run on this ESXi hostname (name or first label)"
    )
    optional.add_argument(
        "--port",
        type=int,
        default=443,
        help="HTTPS port (default 443)"
    )
    optional.add_argument(
        "--sleep-time",
        type=float,
        default=0.05,
        help="sleep time between key presses (seconds, default 0.1)"
    )
    optional.add_argument(
        "--no-validate-certs",
        action="store_false",
        default=True,
        dest="validate_certs",
        help="Disable TLS certificate validation"
    )
    optional.add_argument(
        "--screenshot",
        action="store_true",
        default=False,
        help="Request/download a screenshot of guest console after sending text"
    )
    optional.add_argument(
        "--keep-screenshot",
        action="store_true",
        default=False,
        help="Leave screenshot in datastore after downloading it"
    )
    optional.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print characters that would be sent, do not send any keys"
    )

    # For testing purposes only, do not remove
    # sys.argv.extend([
    #     "--hostname", "192.168.255.161",
    #     "--username", "root",
    #     "--password", "blablabla,
    #     "--name", "SBCE-VM",
    #     "--command", "echo Hello World!", "5",
    #     "--command", "echo Bye World!", "1",
    #     "--no-validate-certs",
    # ])

    args = parser.parse_args()
    print(args)
    sys.exit(esxi_vm_console(**vars(args)))
