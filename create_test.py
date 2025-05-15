import random


def ydarenia():
    def load_words(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read().splitlines()

    def f(word):
        a = ['А', 'Э', 'У', 'О', 'Ы', 'И', 'Ю', 'Я', 'Ё']
        positions = [i for i, ch in enumerate(word) if ch.upper() in a]
        return positions

    def g(word):
        a = f(word)
        b = next((pos for pos in a if word[pos].isupper()), None)

        if b is None or len(a) <= 1:
            return word

        c = [p for p in a if p != b]
        d = random.choice(c)

        letters = list(word)
        letters[b] = letters[b].lower()
        letters[d] = letters[d].upper()
        return ''.join(letters)

    def create_test(words):
        words = random.sample(words, 5)
        number_nepr = random.randint(1, 3)
        nepr = random.sample(range(len(words)), number_nepr)

        questions = {}
        for index, word in enumerate(words):
            if index in nepr:
                questions[index + 1] = {'original': word, 'inaccurate': g(word)}
            else:
                questions[index + 1] = {'original': word, 'inaccurate': word}

        test = "Укажите варианты ответов, в которых правильно выделена буква, обозначающая ударный гласный звук.\n" \
                        "В ответе запишите подходящие номера слов слитно в порядке возрастания."
        for k, v in questions.items():
            test += f"\n{k}) {v['inaccurate']}"

        correct_answer = ''.join(sorted(str(k) for k, v in questions.items() if v['original'] == v['inaccurate']))

        return test, correct_answer

    filename = 'words.txt'
    words = load_words(filename)
    return create_test(words)


def paronimi():
    def load_words(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        words_list = []
        for line in lines:
            parts = line.strip().split(' ')
            if len(parts) >= 2:
                word_pr = parts[0].strip()
                word_nepr = parts[1].strip()
                words_list.append((word_pr, word_nepr))
        return words_list

    def generate_task(words_list):
        a = 5
        d = []
        answer = set()

        while True:
            words = random.sample(words_list, k=a)
            for i, word_pair in enumerate(words):
                prav = bool(random.getrandbits(1))
                word = word_pair[int(prav)]
                d.append(word)
                if not prav:
                    answer.add(i + 1)
            if 1 <= len(answer) <= 3:
                break

        return d, sorted(list(answer)), words

    filename = "7.txt"
    words_list = load_words(filename)
    voprosi, prav, _ = generate_task(words_list)

    test_question = "Выберите из списка слов те, которые записаны в правильной форме во множественном числе:\n" \
                    "В ответе запишите подходящие номера слов слитно в порядке возрастания."
    for idx, option in enumerate(voprosi):
        test_question += f"\n{idx + 1}. {option}"

    prav_otv = ''.join(map(str, prav))

    return test_question, prav_otv


def prepri():
    def load_words(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            words = file.read().splitlines()
        return words

    def vibor(words):
        a = []
        for word in words:
            if any(word.startswith(prefix) for prefix in ['пре', 'при']):
                a.append(word)
            elif 'ъ' in word and word.rindex('ъ') < len(word) - 1:
                a.append(word)
            elif 'ь' in word and word.rindex('ь') < len(word) - 1:
                a.append(word)
        if a:
            return random.choice(a)
        else:
            return None

    def mod(word):
        if "пре" in word.lower():
            index = word.lower().find("пре") + 2
            char = 'е'
        elif "при" in word.lower():
            index = word.lower().find("при") + 2
            char = 'и'
        elif 'ъ' in word and word.rindex('ъ') < len(word) - 1:
            index = word.rindex('ъ')
            char = 'ъ'
        elif 'ь' in word and word.rindex('ь') < len(word) - 1:
            index = word.rindex('ь')
            char = 'ь'
        else:
            raise ValueError("Ошибка: слово не соответствует условиям.")

        modified_word = list(word)
        modified_word[index] = '?'  
        return ''.join(modified_word), char  

    filename = "10.txt"
    words = load_words(filename)
    d = vibor(words)
    modified_word, correct_answer = mod(d)

    test_question = f"Введите пропущенную букву ({modified_word})"

    return test_question, correct_answer.lower() 