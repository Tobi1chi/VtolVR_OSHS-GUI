**Socket命令**

    "name": "sethost",
    "help": "Set host parameters: sethost [name|password|uniticon|campaign|mission] <value>"

    "name": "checkhost",
    "help": "Check current host settings"

    "name": "config",
    "help": "Config a multiplayer game"

    "name": "host",
    "help": "Host a multiplayer game"

    "name": "listscene",
    "help": "List available scenes"

    "name": "start",
    "help": "Start the multiplayer game"

    "name": "skip",
    "help": "Skip current missions"

    "name": "quit",
    "help": "Quit the multiplayer game"

    "name": "restart",
    "help": "Restart the multiplayer game"

    "name": "sendlog",
    "help": "Send a log message to the game: sendlog [message]"

    "name": "player",
    "help": "List connected players"

    "name": "help",
    "help": "Show this help message"

    "name": "list",
    "help": "List actors (type: all/enemy/friendly/air/ground)"

    "name": "test",
    "help": "Run a test command"

    "name": "scene",
    "help": "Get current scene name"

    "name": "readyroom",
    "help": "Go to multiplayer ready room"

    "name": "flightlog",
    "help": "Get flight log entries"

    "name": "getstage",
    "help": "Get current mission stage"

    "name": "exitapp",
    "help": "Exit application"

**开始游戏（首次开始）**

    sethost name SERVERNAME
    sethost password PASSWORD //public server if the PASSWORD is empty
    sethost uniticon false //近距离敌方/友方括号标记
    sethost campaign WSID 
    sethost mission MAP_NAME
    config
    //这里最好delay一分钟
    host
    //等待服务器传回Lobby Created的标识
    start //需要等待host完成

**切换地图（restart）**

    getstage //查看当前任务阶段
    //如果是3-inmission
    skip
    //如果是4a/4b代表任务已经结束，不需要再skip
    
    //重新sethost campaign/sethost mission来切换地图
    //delay一段时间让玩家有机会操作回放/总结聊天
    //这里可以保存flightlog到数据库中
    //另外可以参考Tools/AutoSave_Replay.py里面的内容
    //来将游戏生成的回放文件也一并存起来(文件夹)

    restart
    //等待完成标识LobbyReady
    start //重新开始任务


**任务完成标识**

    //成功config，收到后可以host
    {
    "type": "r",
    "src": "HostConfig",
    "msg": true
    }

    //成功创建房间，收到后可以start
    {
    "type": "s",
    "src": "LobbyReady",
    "msg": ""
    }


**FSM需要做的条件/命令**

    elapsed(int second) //查看运行时间
    //这部分可以用TimerManager（core/Timer.py）来做

    player() //获取当前人数

    delay(int second) //延迟

    set_gv/get_gv/delet_gv //操作用户设定的全局变量
    //如果是直接读取用户写的python脚本的话就不用考虑这块
    //gv应该为静态，需要在加载fsm的时候提前声明

    //这部分后续可能会再加新的，所以最好可以像现在的FSM一样注册指令


**现存的一些Bug**
- Socket运行一段时间之后会出错，然后socket会直接断开连接

**服务器检测**
- 定时刷新player列表/actor列表以及flightlog列表（从服务器获取）
- 如果服务器出现击杀信息(killed/was killed)，这时候我们认为出现了击杀的事件
- 根据flightlog里面显示的击杀事件双方的信息，同时从player列表里面检查双方队伍信息判断是否为有效击杀（或者是TK），查看actor list计算双方位置信息（距离）
- 从数据库中匹配对应的击杀结果（双方机型/武器/当前分数差....)
- 计算出分数变化情况
- 通过sendlog来发送得分变化信息到游戏当中
- 将新的分数保存到数据库里面
