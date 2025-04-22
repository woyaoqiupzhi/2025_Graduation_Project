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
//ALIENTEK Mini STM32��������չʵ��15
//ATK-RM04 WIFIģ�����ʵ��
//����֧�֣�www.openedv.com
//������������ӿƼ����޹�˾  

 int main(void)
 {
	delay_init();	    	 //��ʱ������ʼ��
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2); //����NVIC�жϷ���2:2λ��ռ���ȼ���2λ��Ӧ���ȼ�	  
	uart_init(115200);	 	//���ڳ�ʼ��Ϊ9600	
	USART2_Init(115200);  //��ʼ������2������Ϊ115200
	SPI2_Init();		   	//��ʼ��SPI
	LCD_Init();				//��ʼ��Һ�� 
	LED_Init();         	//LED��ʼ��	 
	KEY_Init();				//������ʼ��
 	mem_init();				//��ʼ���ڴ��	  
	Lcd_Clear(WHITE);	 
	LCD_ShowString(5,20,128,16,16,"System Success!");
	delay_ms(1500);	
	Lcd_Clear(WHITE);//����	       
	atk_8266_test();		//����ATK_ESP8266����
}