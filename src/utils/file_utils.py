"""Tiedosto- ja hakemistotyökalut"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def ensure_directory_exists(directory_path: str) -> None:
    """
    Varmista että hakemisto on olemassa, luo jos ei ole
    
    Args:
        directory_path: Hakemiston polku
        
    Raises:
        PermissionError: Jos ei ole oikeuksia luoda hakemistoa
        OSError: Jos hakemiston luominen epäonnistuu
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)


def get_timestamp(format_string: str = "%Y-%m-%d_%H-%M-%S") -> str:
    """
    Hae nykyinen aikaleima merkkijonona
    
    Args:
        format_string: Strftime-muotoilu
        
    Returns:
        Aikaleima merkkijonona
    """
    return datetime.now().strftime(format_string)


def get_file_size(file_path: str) -> int:
    """
    Hae tiedoston koko tavuina
    
    Args:
        file_path: Tiedoston polku
        
    Returns:
        Tiedoston koko tavuina
        
    Raises:
        FileNotFoundError: Jos tiedostoa ei löydy
    """
    return os.path.getsize(file_path)


def create_backup(file_path: str, backup_suffix: str = ".bak") -> str:
    """
    Luo varmuuskopio tiedostosta
    
    Args:
        file_path: Alkuperäisen tiedoston polku
        backup_suffix: Varmuuskopion pääte
        
    Returns:
        Varmuuskopion polku
        
    Raises:
        FileNotFoundError: Jos alkuperäistä tiedostoa ei löydy
        PermissionError: Jos ei ole oikeuksia luoda varmuuskopiota
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    backup_path = file_path + backup_suffix
    shutil.copy2(file_path, backup_path)
    return backup_path


def cleanup_old_files(directory: str, max_age_days: int = 30, pattern: str = "*") -> int:
    """
    Siivoa vanhat tiedostot hakemistosta
    
    Args:
        directory: Hakemisto josta siivotaan
        max_age_days: Maksimi-ikä päivinä
        pattern: Tiedostonimimalli (glob)
        
    Returns:
        Poistettujen tiedostojen määrä
    """
    if not os.path.exists(directory):
        return 0
    
    from datetime import timedelta
    import glob
    
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0
    
    for file_path in glob.glob(os.path.join(directory, pattern)):
        if os.path.isfile(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError:
                    pass  # Ignore errors
    
    return deleted_count


def safe_write_file(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Turvallinen tiedoston kirjoitus väliaikaisen tiedoston kautta
    
    Args:
        file_path: Kohdetiedoston polku
        content: Kirjoitettava sisältö
        encoding: Merkistökoodaus
        
    Raises:
        PermissionError: Jos ei ole kirjoitusoikeuksia
        OSError: Jos kirjoitus epäonnistuu
    """
    import tempfile
    
    # Varmista että hakemisto on olemassa
    directory = os.path.dirname(file_path)
    if directory:
        ensure_directory_exists(directory)
    
    # Kirjoita väliaikaiseen tiedostoon
    temp_path = file_path + ".tmp"
    try:
        with open(temp_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # Atomisoitu siirto
        shutil.move(temp_path, file_path)
    except Exception:
        # Siivoa väliaikainen tiedosto virhetilanteessa
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def get_disk_usage(path: str) -> dict:
    """
    Hae levytilan käyttötiedot
    
    Args:
        path: Polku jolta tiedot haetaan
        
    Returns:
        Sanakirja jossa total, used, free tavuina
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")
    
    statvfs = os.statvfs(path)
    
    # Laske tavuina
    total = statvfs.f_frsize * statvfs.f_blocks
    free = statvfs.f_frsize * statvfs.f_bavail
    used = total - free
    
    return {
        "total": total,
        "used": used,
        "free": free,
        "percentage_used": (used / total) * 100 if total > 0 else 0
    }


def format_bytes(bytes_count: int) -> str:
    """
    Muotoile tavumäärä ihmisluettavaan muotoon
    
    Args:
        bytes_count: Tavujen määrä
        
    Returns:
        Muotoiltu merkkijono (esim. "1.5 MB")
    """
    if bytes_count == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_count)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def find_files_by_extension(directory: str, extension: str, recursive: bool = True) -> list:
    """
    Etsi tiedostoja tiedostopäätteen perusteella
    
    Args:
        directory: Hakemisto josta etsitään
        extension: Tiedostopääte (ilman pistettä)
        recursive: Etsi myös alihakemistoista
        
    Returns:
        Lista löydetyistä tiedostopoluista
    """
    if not os.path.exists(directory):
        return []
    
    found_files = []
    pattern = f"*.{extension.lstrip('.')}"
    
    if recursive:
        import glob
        search_pattern = os.path.join(directory, "**", pattern)
        found_files = glob.glob(search_pattern, recursive=True)
    else:
        import glob
        search_pattern = os.path.join(directory, pattern)
        found_files = glob.glob(search_pattern)
    
    return [f for f in found_files if os.path.isfile(f)]