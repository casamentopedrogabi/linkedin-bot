def click_connect_sequence(
    browser, button_element, name, headline, group_name, is_viewer=False
):
    """
    SIMPLES E DIRETO: Clica em Conectar → Aguarda modal → Clica "Send without a note"
    Seguindo o padrão proven que funciona.
    """
    global SESSION_CONNECTION_COUNT, CONNECTED, SEND_AI_NOTE

    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        return False

    # PASSO 1: Clica no botão Conectar
    try:
        time.sleep(random.uniform(3, 5))
        browser.execute_script("arguments[0].click();", button_element)
        print(f"    -> Clicou em Conectar para {name}")
    except Exception as e:
        print(f"    -> [ERROR] Falha ao clicar Connect: {e}")
        return False

    # PASSO 2: Aguarda e clica "Send without a note"
    try:
        time.sleep(random.uniform(1, 3))
        xpath_button = "//button[@aria-label='Send without a note']"
        btn = WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.XPATH, xpath_button))
        )
        time.sleep(random.uniform(1, 2))
        btn.click()

        CONNECTED = True
        SESSION_CONNECTION_COUNT += 1
        print(f"    -> [SUCCESS] Invite enviado para: {name}")
        return True

    except TimeoutException:
        print("    -> [TIMEOUT] Botão 'Send without a note' não apareceu")
        return False
    except Exception as e:
        print(f"    -> [ERROR] Falha ao clicar 'Send without a note': {e}")
        return False
