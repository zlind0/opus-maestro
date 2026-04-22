这是一个专门用于古典音乐的播放器项目（同时也兼顾其他类型的音乐）。

# 使用场景

音乐存储在NAS上的若干个文件夹里。服务器使用LLM对音乐进行元数据处理，客户端可以检索元数据并播放。

我们不关心音乐本身叫什么名字，外文怎么拼写，属于哪张专辑，是hebert von karajan指挥的还是karajan指挥的，等等这些文字上的细节，这些都是旧时代的执念。我们关心这是贝多芬的第几交响曲，还是莫扎特的第几协奏曲，谁指挥的，谁演奏的，这首曲子是欢快悲伤还是愤怒。这些元数据在LLM的时代，通过对原来的元数据的处理，已经变为了可能。更进一步讲，在LLM的时代，也可以直接说出，播放莫扎特的第40号交响曲，自动就可以检索到Symphony Nr.40 in G minor。

一切应当尽可能简单，不要给使用者带来太多的操作困惑。庞大的数据库应该通过LLM的简化，变得易于检索。flac和cue的分离，应该变得无感，音量的大小获得统一，所有的技术细节应当隐藏。

# 定义

曲目：一个曲目是一首完整的作品，包含多个乐章，而不是下一个文件。一个曲目可能包含多个文件，每个文件是一个小乐章，组成一个完整的曲目。

# 技术细节

## 后端（Python + FastAPI）

1、推送音乐文件：将各种音乐流化至前端支持的格式播放。至少要支持mp3、aac、alac（apple lossless，要转换成flac）、flac分轨、flac+cue的并轨、ape（为前端转换成flac）。转换使用ffmpeg。

2、索引和检索：普通音乐播放器的精确检索+LLM的模糊检索，包括语音检索、哼唱旋律检索。索引过程放在后台。

3、根据文件的路径、ID3标签等，用LLM提取进阶的元数据【创作年代，文艺复兴、巴洛克、古典、浪漫、现代、后现代等】、作曲家、曲名、调号、编号、情绪、唱词的大意等。生成canonical string:
```
{
  "composer": "Wolfgang Amadeus Mozart",
  "work_title": "Symphony No. 40",
  "key": "G minor",
  "catalog": "K. 550",
  "work_type": "Symphony",
  "era": "Classical",
  "canonical_string": "Composer: Wolfgang Amadeus Mozart | Title: Symphony No. 40 in G minor | Catalog: K. 550 | Type: Symphony | Era: Classical"
}
```
注意，这一部分单独做成一个模块，并且加入测试功能，要求提供一个测试工具，针对某个文件，可以单独输出prompt，以方便调试检验。

4、相似推荐。利用LLM在当前曲目播放完以后推荐下一曲。

5、LLM调OpenAI Compatible的API。

6、注意要支持多语言，第一次设定的语言就是所有字段的语言。默认是简体中文。

## 数据库（Postgres）

最小单位是一个【乐章音频】。一个【乐章音频】可以是一个音频文件，也可以是一个大FLAC中，从一个时间点到另一个时间点的区域。

多个【乐章音频】对应一个【乐章】。多个【乐章】组成一个【曲目】。

一个【乐章】可以通过ID3信息来使用LLM提取【创作风格、作曲家、曲名、调号、编号、情绪】。参考情绪：【欢快/明朗, 悲伤/忧郁, 愤怒/激烈, 宁静/沉思, 神秘/朦胧, 辉煌/庄严, 戏谑/轻快】。

```
-- 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 乐章（物理音频段）
CREATE TABLE audio_segments (
  id UUID PRIMARY KEY,
  file_id UUID REFERENCES audio_files(id),
  start_time_ms INT,
  end_time_ms INT,
  is_virtual BOOLEAN DEFAULT FALSE -- CUE切割产生的虚拟段
);

-- 乐章（逻辑概念）
CREATE TABLE movements (
  movement_id UUID PRIMARY KEY,
  work_id UUID REFERENCES works(work_id),
  movement_number INT,
  movement_title TEXT,
  embedding VECTOR(1536)   -- pgvector
);

-- 曲目/作品（如 贝多芬第五交响曲）
CREATE TABLE works (
  work_id UUID PRIMARY KEY,
  composer TEXT,
  era TEXT,
  work_type TEXT,          -- Symphony, Concerto, Sonata...
  catalog_number TEXT,     -- Op. 67, K. 550, BWV 232...
  title TEXT,
  movement_count INT
);

-- 录音版本（不同指挥/乐团/年代）
CREATE TABLE versions (
  id UUID PRIMARY KEY,
  work_id UUID REFERENCES works(work_id),
  conductor TEXT,
  ensemble TEXT,
  year INT,
  label TEXT
);

-- 关系绑定
-- version 1:N movement
-- movement 1:N audio_segment

```

## 前端（HTML5网页端，做成PWA供移动设备使用，在NAS上serve），技术栈：Vue 3 + TypeScript + Vite + vite-plugin-pwa

前端有鉴权，有账户系统，有管理员账户和听众账户。管理账户可以增删用户，可以管理系统配置。普通听众用户只能收听。每个用户需要存储正在听的播放列表。

1、和常规音乐播放器一样，显示正在播放、上一首、下一首。显示当前播放曲目的时候，要显示多个乐章，高亮当前乐章。下一曲代表下一个曲目。播放的文件要提前拉取，做到曲目间无缝播放。由于是在局域网，提前拉取整个文件。

2、“智能检索”：根据后端LLM分类的【时代->作曲家->类型（交响曲、奏鸣曲、协奏曲等）->曲目->版本(同一曲目的不同录音)->乐章】。

3、“传统检索”：传统的播放器检索，根据作曲家、专辑、等等ID3信息检索。

4、语音指令。响应用户的各种指令，“我要听莫扎特的第35号交响曲”、“贝多芬的愤怒的乐章”等等。选择一类乐曲或者一首乐曲+类似乐曲推荐。

5、播放保活：iOS Safari 对后台标签页音频限制极严。必须完整实现 Media Session API（navigator.mediaSession），声明 title、artist、artwork，并正确绑定 play/pause/prevnext 事件。否则切后台或锁屏后播放极易中断。

# 部署：Docker Compose