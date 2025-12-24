#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BOT SIMPLIFICADO - APENAS TESTE DE CONEXÃO"""

import random
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPEED_FACTOR = 4
DRIVER_FILENAME = "msedgedriver.exe"
BASE_QUICK_CONNECT_URL = "https://www.linkedin.com/search/results/people/?facetNetwork=%5B%22S%22%5D&geoUrn=%5B%22101165590%22%2C%22103350119%22%2C%22102890719%22%2C%22106693272%22%2C%22100364837%22%2C%22105646813%22%2C%22101282230%22%2C%22104738515%22%5D&origin=FACETED_SEARCH"

SESSION_CONNECTION_COUNT = 0
CONNECTION_LIMIT = 5


def get_factored_time(seconds):
    return seconds * SPEED_FACTOR


def human_sleep(min_seconds=2, max_seconds=5):
    base_time = random.uniform(min_seconds, max_seconds)
    time.sleep(get_factored_time(base_time))


def start_browser():
    """Inicia Edge com perfil TEMPORÁRIO"""
    opts = EdgeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("start-maximized")

    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(60)
    return driver


def click_modal_button(browser, name, headline):
    """Testa APENAS o clique do botão modal"""
    global SESSION_CONNECTION_COUNT, CONNECTION_LIMIT

    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        return False

    # 8 seletores diferentes
    selectors = [
        ("XPATH 1", "//button[contains(@aria-label, 'Send without a note')]"),
        ("XPATH 2", "//button[contains(@aria-label, 'Enviar sem nota')]"),
        ("XPATH 3", "//span[contains(text(), 'Send without a note')]/ancestor::button"),
        ("XPATH 4", "//button[.//span[contains(text(), 'Send without a note')]]"),
        (
            "XPATH 5",
            "//div[contains(@class, 'artdeco-modal__actionbar')]//button[contains(@class, 'artdeco-button--primary')]",
        ),
        (
            "XPATH 6",
            "//div[@data-test-modal-id='send-invite-modal']//button[contains(@class, 'artdeco-button--primary')][last()]",
        ),
        ("CSS 7", "div.artdeco-modal__actionbar button.artdeco-button--primary"),
        (
            "XPATH 8",
            "//button[contains(@class, 'artdeco-button--primary') and contains(@class, 'ml1')]",
        ),
    ]

    btn_no_note = None
    matched_selector = None

    for selector_type, selector_value in selectors:
        try:
            if selector_type.startswith("CSS"):
                btn_no_note = WebDriverWait(browser, 1.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector_value))
                )
            else:
                btn_no_note = WebDriverWait(browser, 1.5).until(
                    EC.element_to_be_clickable((By.XPATH, selector_value))
                )

            if btn_no_note:
                matched_selector = selector_type
                print("    ✅ Modal encontrado com: " + selector_type)
                break
        except Exception:
            continue

    if btn_no_note:
        print("    ➜ Clicando botão...")
        browser.execute_script("arguments[0].click();", btn_no_note)
        human_sleep(3, 5)
        print("    ✅ BOTÃO CLICADO COM SUCESSO!")
        SESSION_CONNECTION_COUNT += 1
        return True
    else:
        print("    ⚠️ Tentando JavaScript puro...")

        js_code = """
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            var ariaLabel = buttons[i].getAttribute('aria-label');
            var textContent = buttons[i].textContent;
            if (ariaLabel && ariaLabel.includes('Send without a note')) {
                buttons[i].click();
                return 'aria-label match';
            }
            if (textContent && textContent.includes('Send without a note') &&
                buttons[i].className.includes('artdeco-button--primary')) {
                buttons[i].click();
                return 'text match';
            }
        }
        return 'not found';
        """

        result = browser.execute_script(js_code)
        print("    📊 JS result: " + str(result))

        if result != "not found":
            human_sleep(3, 5)
            SESSION_CONNECTION_COUNT += 1
            return True
        else:
            print("    ❌ Botão não encontrado!")
            return False


def run_test():
    """Testa conexão"""
    global SESSION_CONNECTION_COUNT

    print("\n" + "=" * 60)
    print("🤖 BOT TESTE CONEXÃO")
    print("=" * 60 + "\n")

    driver = None
    try:
        print("📱 Iniciando Edge...")
        driver = start_browser()
        print("✅ Edge iniciado\n")

        print("📄 Abrindo LinkedIn...")
        driver.get(BASE_QUICK_CONNECT_URL)
        human_sleep(8, 12)
        print("✅ Página carregada\n")

        print("📜 Scrollando...")
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            human_sleep(2, 3)
        driver.execute_script("window.scrollTo(0, 0);")
        print("✅ Scroll concluído\n")

        print("🔍 Procurando botões Invite...")
        try:
            invites = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//a[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
                    )
                )
            )
            print("✅ Encontrados " + str(len(invites)) + " botões\n")
        except Exception as e:
            print("❌ Erro: " + str(e))
            return False

        if not invites:
            print("❌ Nenhum botão encontrado")
            return False

        print("🎯 Testando PRIMEIRO botão...\n")
        first = invites[0]

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", first
        )
        human_sleep(2, 3)

        print("  ➜ Clicando botão Invite...")
        driver.execute_script("arguments[0].click();", first)
        print("  ✅ Botão clicado")
        human_sleep(4, 7)

        print("\n  ➜ Testando modal...\n")
        success = click_modal_button(driver, "User", "Headline")

        if success:
            print("\n✅✅✅ SUCESSO! BOTÃO FOI CLICADO!")
            print(
                "📊 Conexões: "
                + str(SESSION_CONNECTION_COUNT)
                + "/"
                + str(CONNECTION_LIMIT)
                + "\n"
            )
            return True
        else:
            print("\n❌ Falha ao clicar botão")
            return False

    except Exception as e:
        print("\n❌ ERRO: " + str(e))
        import traceback

        traceback.print_exc()
        return False

    finally:
        if driver:
            print("\n🛑 Fechando navegador...")
            try:
                driver.quit()
                print("✅ Fechado\n")
            except Exception:
                pass


if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)
