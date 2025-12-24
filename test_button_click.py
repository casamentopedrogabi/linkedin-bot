#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TESTE: Usa EXATAMENTE o mesmo jeito de iniciar Edge do bot
Testa o clique em 'Send without a note' na pagina de Quick Connect
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

print("=" * 80)
print("TESTE: 'Send without a note' com mesmo jeito de iniciar do bot")
print("=" * 80)

DRIVER_FILENAME = "msedgedriver.exe"
BASE_QUICK_CONNECT_URL = "https://www.linkedin.com/search/results/people/?facetNetwork=%5B%22S%22%5D&geoUrn=%5B%22101165590%22%2C%22103350119%22%2C%22102890719%22%2C%22106693272%22%2C%22100364837%22%2C%22105646813%22%2C%22101282230%22%2C%22104738515%22%5D&origin=FACETED_SEARCH"

# EXATAMENTE como o bot faz
opts = EdgeOptions()
ud = os.path.join(
    os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data"
)
opts.add_argument(f"--user-data-dir={ud}")
opts.add_argument("--profile-directory=Default")

try:
    print("\n[1] Inicializando Edge (mesmo jeito do bot)...")
    service = EdgeService(executable_path=DRIVER_FILENAME)
    driver = webdriver.Edge(options=opts, service=service)
    driver.set_page_load_timeout(60)
    print("    [OK] Edge iniciado")
except Exception as e:
    print("[ERRO] Falha ao iniciar Edge: " + str(e))
    sys.exit(1)

try:
    # Acessar a mesma URL que o bot usa
    print("\n[2] Abrindo BASE_QUICK_CONNECT_URL...")
    driver.get(BASE_QUICK_CONNECT_URL)
    time.sleep(10)

    print("[3] Procurando botoes 'Invite...to connect'...")

    # Scroll para carregar resultados
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    # Procurar por links de invite
    invite_links = driver.find_elements(
        By.XPATH,
        "//a[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
    )

    print("    Encontrados " + str(len(invite_links)) + " botoes Invite")

    if len(invite_links) == 0:
        print("    [AVISO] Nao encontrados invite links nesta pagina")
        driver.quit()
        sys.exit(0)

    # Clicar no primeiro invite
    print("\n[4] Clicando no primeiro 'Invite to connect'...")
    first_invite = invite_links[0]

    # Extrair nome do aria-label
    aria_label = first_invite.get_attribute("aria-label")
    name = aria_label.split(" ")[0] if aria_label else "Unknown"
    print("    Nome: " + name)

    # Scroll para o elemento
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        first_invite,
    )
    time.sleep(1)

    # Clicar
    driver.execute_script("arguments[0].click();", first_invite)
    time.sleep(5)

    # Aguardar e verificar modal
    print("\n[5] Aguardando modal...")
    try:
        modal = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@data-test-modal-id='send-invite-modal']")
            )
        )
        print("    [OK] Modal encontrado!\n")

        # Testar seletores (mesmos que estao em bot_v2.py)
        print("[6] Testando seletores para 'Send without a note':\n")

        selectors = [
            ("XPATH", "//button[contains(@aria-label, 'Send without a note')]"),
            ("XPATH", "//button[contains(@aria-label, 'Enviar sem nota')]"),
            (
                "XPATH",
                "//span[contains(text(), 'Send without a note')]/ancestor::button",
            ),
            ("XPATH", "//button[.//span[contains(text(), 'Send without a note')]]"),
            (
                "XPATH",
                "//div[contains(@class, 'artdeco-modal__actionbar')]//button[contains(@class, 'artdeco-button--primary')]",
            ),
            (
                "XPATH",
                "//div[@data-test-modal-id='send-invite-modal']//button[contains(@class, 'artdeco-button--primary')][last()]",
            ),
            ("CSS", "div.artdeco-modal__actionbar button.artdeco-button--primary"),
            (
                "XPATH",
                "//button[contains(@class, 'artdeco-button--primary') and contains(@class, 'ml1')]",
            ),
        ]

        send_btn = None
        working_index = 0

        for i, (sel_type, sel_value) in enumerate(selectors, 1):
            try:
                if sel_type == "CSS":
                    send_btn = WebDriverWait(driver, 1.5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel_value))
                    )
                else:
                    send_btn = WebDriverWait(driver, 1.5).until(
                        EC.element_to_be_clickable((By.XPATH, sel_value))
                    )

                print("    [OK] Seletor " + str(i) + " funcionou (" + sel_type + ")")
                aria_label = send_btn.get_attribute("aria-label")
                text = send_btn.text.strip()
                if aria_label:
                    print("        aria-label: " + aria_label)
                if text:
                    print("        text: " + text)
                print()

                working_index = i
                break

            except Exception:
                continue

        if send_btn:
            print("[7] Clicando 'Send without a note'...")
            driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(3)

            print("    [OK] Botao clicado!")

            # Verificar se modal fechou
            time.sleep(2)
            try:
                driver.find_element(
                    By.XPATH, "//div[@data-test-modal-id='send-invite-modal']"
                )
                print("    [AVISO] Modal ainda visivel")
            except Exception:
                print("    [OK] Modal desapareceu!\n")

            print("=" * 80)
            print("SUCESSO! Botao clicado com seletor " + str(working_index))
            print("=" * 80)
        else:
            print("[FAIL] Nenhum seletor funcionou")

            # Tentar JS como fallback
            print("\n[8] Tentando JavaScript puro...")
            js_code = """
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                if (buttons[i].getAttribute('aria-label') && 
                    buttons[i].getAttribute('aria-label').includes('Send without a note')) {
                    buttons[i].click();
                    return true;
                }
                if (buttons[i].textContent && 
                    buttons[i].textContent.includes('Send without a note') &&
                    buttons[i].className.includes('artdeco-button--primary')) {
                    buttons[i].click();
                    return true;
                }
            }
            return false;
            """
            result = driver.execute_script(js_code)

            if result:
                print("    [OK] JavaScript funcionou!")
            else:
                print("    [FAIL] JavaScript tambem falhou")

    except Exception as e:
        print("    [FAIL] Modal nao encontrado: " + str(e)[:60])

    time.sleep(3)

except Exception as e:
    print("[ERRO] " + str(e)[:100])

finally:
    print("\nEncerrando...")
    driver.quit()
    print("Teste finalizado.")
