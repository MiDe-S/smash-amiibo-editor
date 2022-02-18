import PySimpleGUI as sg
from re import sub


def load_from_txt(file_path):
    """
    Loads sections from regions.txt

    :param file_path: file path to regions.txt
    :return: list of sections
    """
    sections = []
    with open(file_path, 'r') as fp:
        region_file = fp.read()
        region_file = region_file.split("\n\n")
    for region in region_file:
        section = None
        parts = region.split('\n')
        section_type = parts[0].split(':')
        if section_type[1].strip() == "ABILITY":
            options = load_ability_file()
            section = ENUM(int(parts[1], 16), 8, section_type[0], parts[-1], options, 0)

        elif section_type[1].strip() == "ENUM":
            # bit length is calculated by byte end - byte start * 8
            if 'b' in parts[2] or 'b' in parts[1]:
                end_loc = parts[2].split('b')
                start_loc = parts[1].split('b')
                # bit end + 8 - bit start + byte end - byte start - 1
                # -1 is to account for byte included with bits
                bit_length = int(end_loc[1]) + 8 - int(start_loc[1]) + 8*(int(end_loc[0], 16) - int(start_loc[0], 16)) - 8

                # for initializing class
                start_location = start_loc[0]
                bit_start_location = start_loc[1]
            else:
                bit_length = 8*(int(parts[2], 16) - int(parts[1], 16))

                # for initializing class
                start_location = parts[1]
                bit_start_location = 0

            options = {}
            options_found = False
            for line in parts:
                # before so '{' line isn't included
                if line == "}":
                    options_found = False
                if options_found:
                    option = line.split(':')
                    if 'b' in option[1]:
                        value = int(option[1], 2)
                    else:
                        value = int(option[1])
                    options[option[0].strip()] = value
                # after so '{' line isn't included
                if line == '{':
                    options_found = True

            section = ENUM(int(start_location, 16), bit_length, section_type[0], parts[-1], options, int(bit_start_location))

        elif section_type[1].strip() == "u8":
            section = unsigned(int(parts[1], 16), 8, section_type[0], parts[-1])

        elif section_type[1].strip() == "u16":
            section = unsigned(int(parts[1], 16), 16, section_type[0], parts[-1])

        elif section_type[1].strip() == "i8":
            section = signed(int(parts[1], 16), 8, section_type[0], parts[-1])

        elif section_type[1].strip() == "i16":
            section = signed(int(parts[1], 16), 16, section_type[0], parts[-1])

        elif section_type[1].strip() == "bits":
            if 'b' in parts[2] or 'b' in parts[1]:
                end_loc = parts[2].split('b')
                start_loc = parts[1].split('b')
                # bit end + 8 - bit start + byte end - byte start - 1
                # -1 is to account for byte included with bits
                bit_length = int(end_loc[1]) + 8 - int(start_loc[1]) + 8 * (
                            int(end_loc[0], 16) - int(start_loc[0], 16)) - 8

                # for initializing class
                start_location = start_loc[0]
                bit_start_location = start_loc[1]
            else:
                bit_length = 8 * (int(parts[2], 16) - int(parts[1], 16))

                # for initializing class
                start_location = parts[1]
                bit_start_location = 0

            section = bits(int(start_location, 16), bit_length, section_type[0], parts[-1], int(bit_start_location))

        else:
            pass
        if section is not None:
            sections.append(section)
    return sections


def load_ability_file():
    with open('resources/abilities.txt') as abilities:
        current_ability = 0
        spirit_dict = {}
        for lines in abilities.readlines():
            spirit_dict[lines.replace('â†‘', 'Up ').replace('â†“', 'Down ').strip('\n')] = current_ability
            current_ability += 1
        return spirit_dict


def load_from_json(file_path):
    """
    Loads sections from regions.json

    :param file_path: file path to regions.json
    :return: list of sections
    """
    pass


def validate_number(value):
    # regex for removing all non signed float characters https://regexlib.com/Search.aspx?k=float&AspxAutoDetectCookieSupport=1
    value = sub("[^-?\d+(\.\d+)?$]", '', value)
    if value == '':
        return 0
    if value[-1] == '.':
        value += '0'
    if value.rfind('-') != 0:
        value = ''.join(value.rsplit('-', 1))
    try:
        float(value)
    except ValueError:
        return 0
    return value


class Section:
    def __init__(self, start_location, length, name, description):
        self.start_location = start_location
        self.length = length
        self.name = name
        self.description = description

        self.primary_input_key = None

    def get_widget(self, key_index):
        self.primary_input_key = key_index
        key_index += 1
        return [[sg.Text(self.name)],
                [sg.Text(self.description)]], key_index

    def get_keys(self):
        return [self.primary_input_key]


class ByteWise(Section):
    def __init__(self, start_location, length, name, description, maximum, minimum=0):
        """

        :param int start_location: start location as int
        :param int length: number of bits as int
        :param str name: name as str
        :param str description: description
        :param int maximum: range maximum
        :param int minimum: range minimum
        """
        super().__init__(start_location, length, name, description)
        self.max = maximum
        self.min = minimum

    def validate_input(self, value):
        value = sub("[^-?\d+)?$]", '', value)
        while value.rfind('-') > 0:
            value = ''.join(value.rsplit('-', 1))

        if value == '' or value == '-':
            return value
        value = int(value)

        if value > self.max:
            value = self.max
        elif value < self.min:
            value = self.min

        return str(value)

    def get_widget(self, key_index):
        layout, new_index = super().get_widget(key_index)

        # noinspection PyTypeChecker
        layout[0].append(sg.Input(enable_events=True, key=self.primary_input_key, default_text=0, size=(10, None)))
        return layout, new_index

    def update(self, event_key, window, amiibo, value):
        # handles when bin is first loaded
        if event_key == "LOAD_AMIIBO" or event_key == "Open":
            value = self.get_value_from_bin(amiibo)

            window[self.primary_input_key].update(value)
            # no need to validate since value came from bin
            validated = value
        else:
            validated = self.validate_input(value)
            if validated != value:
                window[self.primary_input_key].update(validated)
            if validated == "" or validated == "-":
                validated = 0
        return validated


class RangeNum(Section):
    def __init__(self, start_location, length, name, description, maximum, minimum=0, resolution=1):
        """

        :param int start_location: start location as int
        :param int length: number of bits as int
        :param str name: name as str
        :param str description: description
        :param int maximum: range maximum
        :param int minimum: range minimum
        :param float resolution: range resolution (how much it jumps by)
        """
        super().__init__(start_location, length, name, description)
        self.max = maximum
        self.min = minimum
        self.resolution = resolution

        self.secondary_input_key = None

    def get_widget(self, key_index):
        layout, new_index = super().get_widget(key_index)
        key_index = new_index
        # noinspection PyTypeChecker
        layout[0].append(
            sg.Slider(key=self.primary_input_key, range=(self.min, self.max), orientation='horizontal', default_value=0,
                      disable_number_display=True, enable_events=True, resolution=self.resolution))
        self.secondary_input_key = key_index
        key_index += 1
        # noinspection PyTypeChecker
        layout[0].append(sg.Input(enable_events=True, key=self.secondary_input_key, default_text=0, size=(10, None)))
        return layout, key_index

    def get_keys(self):
        key_list = super().get_keys()
        key_list.append(self.secondary_input_key)
        return key_list

    def update(self, event_key, window, amiibo, value):
        if event_key == self.primary_input_key:
            window[self.secondary_input_key].update(value)
        elif event_key == self.secondary_input_key:
            if value > self.max:
                value = self.max
            elif value < self.min:
                value = self.min

            window[self.primary_input_key].update(value)
            window[self.secondary_input_key].update(value)
        # handles when bin is first loaded
        elif event_key == "LOAD_AMIIBO" or event_key == "Open":
            value = self.get_value_from_bin(amiibo)

            window[self.primary_input_key].update(value)
            window[self.secondary_input_key].update(value)
        return value


class unsigned(ByteWise):
    """
    Unsigned bytes only
    """
    def __init__(self, start_location, length, name, description):
        """

        :param int start_location: start location as int
        :param int length: number of bits as int
        :param str name: name as str
        :param str description: description
        """
        super().__init__(start_location, length, name, description, 2 ** length - 1)

    def get_widget(self, key_index):
        return super().get_widget(key_index)

    def get_value_from_bin(self, amiibo):
        if amiibo is None:
            return 0
        if self.length > 8:
            return int.from_bytes(amiibo.get_bytes(self.start_location, self.start_location+self.length//8), "little")
        else:
            return amiibo.get_bytes(self.start_location)

    def set_value_in_bin(self, amiibo, value):
        amiibo.set_bytes(self.start_location, value.to_bytes(self.length//8, 'little'))

    def update(self, event_key, window, amiibo, value):
        value = super().update(event_key, window, amiibo, value)
        if amiibo is not None:
            self.set_value_in_bin(amiibo, int(value))


class signed(ByteWise):
    def __init__(self, start_location, length, name, description):
        """

        :param int start_location: start location as int
        :param int length: number of bits as int
        :param str name: name as str
        :param str description: description
        """
        super().__init__(start_location, length, name, description, 2 ** length // 2 - 1, 2 ** length // -2)

    def get_widget(self, key_index):
        return super().get_widget(key_index)

    def get_value_from_bin(self, amiibo):
        if amiibo is None:
            return 0
        if self.length > 8:
            return int.from_bytes(amiibo.get_bytes(self.start_location, self.start_location+self.length//8), "little", signed=True)
        else:
            return amiibo.get_bytes(self.start_location)

    def set_value_in_bin(self, amiibo, value):
        amiibo.set_bytes(self.start_location, value.to_bytes(self.length//8, 'little', signed=True))

    def update(self, event_key, window, amiibo, value):
        value = super().update(event_key, window, amiibo, value)
        if amiibo is not None:
            self.set_value_in_bin(amiibo, int(value))


class bits(RangeNum):
    def __init__(self, start_location, length, name, description, bit_start_location):
        super().__init__(start_location, length, name, description, 100, resolution=1/(2**length-1))
        self.bit_start_location = bit_start_location

    def get_widget(self, key_index):
        return super().get_widget(key_index)

    def get_value_from_bin(self, amiibo):
        if amiibo is None:
            return 0
        value = amiibo.get_bits(self.start_location, self.bit_start_location, self.length)
        return value / (2**self.length-1) * 100

    def set_value_in_bin(self, amiibo, value):
        # rounding is needed because int always rounds down
        value = int(round(value / 100 * (2**self.length - 1), 0))
        amiibo.set_bits(self.start_location, self.bit_start_location, self.length, value)

    def get_keys(self):
        return super().get_keys()

    def update(self, event_key, window, amiibo, value):
        if value is not None and event_key == self.secondary_input_key:
            value = validate_number(value)
            # so you can use arrow keys/clear num box
            if value == self.get_value_from_bin(amiibo):
                return 0
        value = super().update(event_key, window, amiibo, value)
        if amiibo is not None:
            self.set_value_in_bin(amiibo, value)


class ENUM(Section):
    def __init__(self, start_location, length, name, description, options, bit_start_location):
        super().__init__(start_location, length, name, description)
        self.options = options
        self.bit_start_location = bit_start_location

    def get_widget(self, key_index):
        layout, new_index = super().get_widget(key_index)
        key_index = new_index
        option_list = list(self.options.keys())
        # noinspection PyTypeChecker
        layout[0].append(sg.Combo(option_list, key=self.primary_input_key, default_value=option_list[0], enable_events=True, readonly=True))
        return layout, key_index

    def get_value_from_bin(self, amiibo):
        if amiibo is None:
            return 0
        # for if ENUM is bytewise
        value = amiibo.get_bits(self.start_location, self.bit_start_location, self.length)
        for key in self.options:
            if value == self.options[key]:
                return key
        # if value not found default to first option
        return list(self.options.keys())[0]

    def set_value_in_bin(self, amiibo, value):
        # rounding is needed because int always rounds down
        amiibo.set_bits(self.start_location, self.bit_start_location, self.length, self.options[value])

    def get_keys(self):
        return super().get_keys()

    def update(self, event_key, window, amiibo, value):
        if event_key == "LOAD_AMIIBO" or event_key == "Open":
            window[self.primary_input_key].update(self.get_value_from_bin(amiibo))
        elif amiibo is not None:
            self.set_value_in_bin(amiibo, value)


# class for text such as nicknames
class Text(Section):
    pass
