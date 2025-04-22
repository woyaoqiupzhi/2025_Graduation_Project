#include "led.h"
#include "delay.h"
#include "sys.h"
#include "usart.h"
#include "lcd.h"
#include "key.h"
#include "spi.h"
#include "malloc.h"
#include "text.h"	
#include "common.h"
#include "usart2.h"	
//ALIENTEK Mini STM32开发板扩展实验15
//ATK-RM04 WIFI模块测试实验
//技术支持：www.openedv.com
//广州市星翼电子科技有限公司  

 int main(void)
 {
	delay_init();	    	 //延时函数初始化
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2); //设置NVIC中断分组2:2位抢占优先级，2位响应优先级	  
	uart_init(115200);	 	//串口初始化为9600	
	USART2_Init(115200);  //初始化串口2波特率为115200
	SPI2_Init();		   	//初始化SPI
	LCD_Init();				//初始化液晶 
	LED_Init();         	//LED初始化	 
	KEY_Init();				//按键初始化
 	mem_init();				//初始化内存池	  
	Lcd_Clear(WHITE);	 
	LCD_ShowString(5,20,128,16,16,"System Success!");
	delay_ms(1500);	
	Lcd_Clear(WHITE);//清屏	       
	atk_8266_test();		//进入ATK_ESP8266测试
}