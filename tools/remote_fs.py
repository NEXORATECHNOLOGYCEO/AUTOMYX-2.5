"""
AUTOMYX — ARCHIVOS REMOTOS (SFTP sobre SSH)
===========================================
write_file/edit_file son LOCALES: si el modelo intenta escribir en /var/www/...
de un servidor, o falla o escribe en el disco local. Estas tools operan sobre el
sistema de archivos del SERVIDOR remoto, así el agente puede REALMENTE modificar
webs y apps desplegadas (editar templates, configs, subir archivos).
"""
from __future__ import annotations

from typing import Any, Dict


def _sftp(host, user, password, key_path, port):
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ck = {"hostname": host, "port": int(port or 22), "username": user or "root",
          "timeout": 20, "allow_agent": False, "look_for_keys": bool(key_path)}
    if key_path:
        ck["key_filename"] = key_path
    elif password:
        ck["password"] = password
    ssh.connect(**ck)
    return ssh, ssh.open_sftp()


def _common(kwargs):
    return (kwargs.get("host") or kwargs.get("ip"),
            kwargs.get("user") or kwargs.get("username") or "root",
            kwargs.get("password"),
            kwargs.get("key_path") or kwargs.get("key"),
            int(kwargs.get("port") or 22))


class RemoteFS:
    @staticmethod
    def ssh_read_file(**kwargs) -> str:
        """Lee un archivo del SERVIDOR remoto por SFTP. SIEMPRE léelo antes de
        editarlo. Args: host, path, user, password/key_path, port."""
        host, user, password, key_path, port = _common(kwargs)
        path = kwargs.get("path") or kwargs.get("file") or kwargs.get("remote_path")
        if not host or not path:
            return "❌ Error: Se requiere 'host' y 'path'."
        try:
            ssh, sftp = _sftp(host, user, password, key_path, port)
            with sftp.open(path, "r") as f:
                data = f.read().decode("utf-8", errors="replace")
            sftp.close(); ssh.close()
            n = data.count("\n") + 1
            return f"[{path} · {n} líneas · {len(data)} bytes]\n{data[:6000]}" + (
                "\n… (truncado)" if len(data) > 6000 else "")
        except Exception as e:
            return f"❌ ssh_read_file falló: {str(e)[:200]}"

    @staticmethod
    def ssh_write_file(**kwargs) -> str:
        """Escribe/crea un archivo en el SERVIDOR remoto por SFTP (crea la ruta
        si hace falta). Para archivos GRANDES usa ssh_append_file por partes.
        Args: host, path, content, user, password/key_path, port."""
        host, user, password, key_path, port = _common(kwargs)
        path = kwargs.get("path") or kwargs.get("file") or kwargs.get("remote_path")
        content = kwargs.get("content")
        if content is None:
            content = kwargs.get("text") or ""
        if not host or not path:
            return "❌ Error: Se requiere 'host' y 'path'."
        try:
            ssh, sftp = _sftp(host, user, password, key_path, port)
            # crear directorios padre
            import posixpath
            d = posixpath.dirname(path)
            if d:
                parts, cur = d.strip("/").split("/"), ""
                for p in parts:
                    cur += "/" + p
                    try:
                        sftp.stat(cur)
                    except IOError:
                        try:
                            sftp.mkdir(cur)
                        except Exception:
                            pass
            with sftp.open(path, "w") as f:
                f.write(str(content))
            size = sftp.stat(path).st_size
            sftp.close(); ssh.close()
            return f"✅ Escrito {path} en {host} ({size} bytes)."
        except Exception as e:
            return f"❌ ssh_write_file falló: {str(e)[:200]}"

    @staticmethod
    def ssh_append_file(**kwargs) -> str:
        """Añade contenido al FINAL de un archivo remoto (para escribir archivos
        grandes por partes). Args: host, path, content, user, password/key_path."""
        host, user, password, key_path, port = _common(kwargs)
        path = kwargs.get("path") or kwargs.get("file") or kwargs.get("remote_path")
        content = kwargs.get("content") or kwargs.get("text") or ""
        if not host or not path:
            return "❌ Error: Se requiere 'host' y 'path'."
        try:
            ssh, sftp = _sftp(host, user, password, key_path, port)
            try:
                with sftp.open(path, "r") as f:
                    prev = f.read().decode("utf-8", errors="replace")
            except IOError:
                prev = ""
            with sftp.open(path, "w") as f:
                f.write(prev + str(content))
            size = sftp.stat(path).st_size
            sftp.close(); ssh.close()
            return f"✅ Añadido a {path} (+{len(str(content))} chars, ahora {size} bytes)."
        except Exception as e:
            return f"❌ ssh_append_file falló: {str(e)[:200]}"

    @staticmethod
    def ssh_edit_file(**kwargs) -> str:
        """Edición QUIRÚRGICA de un archivo remoto: reemplaza old_string (exacto y
        único) por new_string. Hace backup .bak automático. Args: host, path,
        old_string, new_string, replace_all, user, password/key_path."""
        host, user, password, key_path, port = _common(kwargs)
        path = kwargs.get("path") or kwargs.get("file") or kwargs.get("remote_path")
        old = kwargs.get("old_string") if kwargs.get("old_string") is not None else kwargs.get("old")
        new = kwargs.get("new_string") if kwargs.get("new_string") is not None else kwargs.get("new", "")
        replace_all = bool(kwargs.get("replace_all"))
        if not host or not path or old is None:
            return "❌ Error: Se requiere 'host', 'path' y 'old_string'."
        try:
            ssh, sftp = _sftp(host, user, password, key_path, port)
            with sftp.open(path, "r") as f:
                src = f.read().decode("utf-8", errors="replace")
            old, new = str(old), str(new)
            n = src.count(old)
            if n == 0:
                sftp.close(); ssh.close()
                return ("❌ old_string NO aparece en el archivo remoto. Léelo con "
                        "ssh_read_file y copia el fragmento EXACTO.")
            if n > 1 and not replace_all:
                sftp.close(); ssh.close()
                return f"❌ old_string aparece {n} veces — añade contexto o usa replace_all=true."
            new_src = src.replace(old, new) if replace_all else src.replace(old, new, 1)
            with sftp.open(path + ".bak", "w") as f:
                f.write(src)
            with sftp.open(path, "w") as f:
                f.write(new_src)
            sftp.close(); ssh.close()
            reps = n if replace_all else 1
            return f"✅ {path} editado en {host} ({reps} reemplazo(s), backup en {path}.bak)."
        except Exception as e:
            return f"❌ ssh_edit_file falló: {str(e)[:200]}"

    @staticmethod
    def ssh_upload(**kwargs) -> str:
        """Sube un archivo LOCAL a un servidor remoto por SFTP.
        Args: host, local_path, remote_path, user, password/key_path, port."""
        host, user, password, key_path, port = _common(kwargs)
        local = kwargs.get("local_path") or kwargs.get("local") or kwargs.get("src")
        remote = kwargs.get("remote_path") or kwargs.get("remote") or kwargs.get("dest") or kwargs.get("path")
        if not host or not local or not remote:
            return "❌ Error: Se requiere 'host', 'local_path' y 'remote_path'."
        import os
        if not os.path.exists(local):
            return f"❌ No existe el archivo local: {local}"
        try:
            ssh, sftp = _sftp(host, user, password, key_path, port)
            sftp.put(local, remote)
            size = sftp.stat(remote).st_size
            sftp.close(); ssh.close()
            return f"✅ Subido {local} → {host}:{remote} ({size} bytes)."
        except Exception as e:
            return f"❌ ssh_upload falló: {str(e)[:200]}"
