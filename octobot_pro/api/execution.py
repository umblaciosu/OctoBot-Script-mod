#  This file is part of OctoBot-Pro (https://github.com/Drakkar-Software/OctoBot-Pro)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot-Pro. If not, see <https://www.gnu.org/licenses/>.

import octobot_pro.internal.logging_util as logging_util
import octobot_pro.internal.runners as runners


async def run(backtesting_data, update_func, strategy_config,
              enable_logs=False, enable_storage=True):
    if enable_logs:
        logging_util.load_logging_config()
    return await runners.run(
        backtesting_data, update_func, strategy_config,
        enable_logs=enable_logs, enable_storage=enable_storage
    )
