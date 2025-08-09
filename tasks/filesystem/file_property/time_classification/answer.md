
文件结构

07/
 ├─ 09/ (sg.jpg, metadata_analyse.txt)
 ├─ 25/ (bus.MOV, metadata_analyse.txt)
 └─ 26/ (road.MOV, metadata_analyse.txt)
08/
 └─ 06/ (bear.jpg, bridge.jpg, random_file_1.txt, random_file_2.txt, random_file_3.txt, metadata_analyse.txt)

以上文件夹必须按照这个路径分布，其他文件不管。

然后metadata_analyse.txt里面：

07 09的，两行都是sg.jpg, 日期包含7， 9，2025这仨数就行

07 25的，两行都是bus.MOV, 日期包含7， 25，2025这仨数就行

07 26的，两行都是road.MOV, 日期包含7， 26，2025这仨数就行

08 06的，oldest是bear, 日期包含7， 26，2025这仨数就行;latest是random_file_1.txt, random_file_2.txt, random_file_3.txt 这三个有其中一个就算对, 日期包含06， 08，2025这仨数就行
