

## nb_agent_bfzs 项目文件结构注意：

1. nb_agent_bfzs 只是演示 nb_agent框架的一个项目，是为了演示使用 nb-agent框架如何扩展 提示词 skill  tool mcp，不是最终的服务某个特定功能的产品，是个演示demo大杂烩 。

2. skills 文件夹下是随意写的假的skill演示例子，不是本项目最终agent产品所需的，主要是为了演示skill的编写规则，遵循 agentskill.io 规范。

3. mcp_servers 文件夹下的mcp，不是本项目最终agent产品所需的，只是为了演示用户如何自定义定义自己的mcp，而不是只会依靠配置第三方mcp。

4. tools 文件夹下的工具函数，不是本项目最终agent产品所需的，只是为了演示用户如何在nb_agent框架中自定义tool函数，自动暴露给ai的请求协议的function字段


## 用户如何让 nb-agent 作为ai coding 来使用

可以在tui界面，点击agents按钮或者按f4，可以配置一个专属的 ai coding 智能体(但是如果你只搞编程，不精确搞10几个作用场景用途，那也可以不用专门配专门的编程agent)，在这个智能体要绑定 serena 这个mcp。

serena mcp的每个函数已经暴露了 入参和作用给ai，如果要让ai更精通serena，你还可以专门写一个skill，或者写在pomote提示词也行。

### 注意：

如果要实现编程，只需要介入 serena 这一个mcp就可以了，不要再接各种乱七八糟的mcp。 serena专门为编程而生，具备精确的 索引 读 写 执行 操作，在编程场景吊打通用的 fielsystem mcp读写。
nb-agent化身编程终端，只需要接入serena 这一个mcp就可以了，不要再另外接入其他乱七八糟的file system 和 codegraph 这些mcp。


