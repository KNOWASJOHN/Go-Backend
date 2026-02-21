package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/skip2/go-qrcode"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/proto/waE2E"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

var (
	targetJID      types.JID
	targetJIDMutex sync.RWMutex
	client         *whatsmeow.Client
	dbContainer    *sqlstore.Container

	chatHistory    = make(map[string][]string)
	historyMutex   sync.Mutex
)

func main() {
	// 1. Database & Session Persistence
	dbLog := waLog.Stdout("Database", "ERROR", true)
	var err error
	dbContainer, err = sqlstore.New(context.Background(), "sqlite3", "file:whatsapp_session.db?_foreign_keys=on", dbLog)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	deviceStore, err := dbContainer.GetFirstDevice(context.Background())
	if err != nil {
		log.Fatalf("Failed to get device store: %v", err)
	}

	// 2. Initialize Client
	clientLog := waLog.Stdout("Client", "ERROR", true)
	client = whatsmeow.NewClient(deviceStore, clientLog)
	client.AddEventHandler(eventHandler)

	// 3. Connect & Authenticate
	if client.Store.ID == nil {
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			log.Fatalf("Connection failed: %v", err)
		}
		for evt := range qrChan {
			if evt.Event == "code" {
				fmt.Println("\n--- QR CODE GENERATED ---")
				err = qrcode.WriteFile(evt.Code, qrcode.Medium, 256, "qr.png")
				if err != nil {
					fmt.Printf("Failed to generate QR code file: %v\n", err)
				} else {
					fmt.Println("QR code saved to 'qr.png'. Please open this file and scan it.")
				}
				fmt.Println("QR code string:", evt.Code)
			} else {
				fmt.Println("Login event:", evt.Event)
			}
		}
	} else {
		err = client.Connect()
		if err != nil {
			log.Fatalf("Connection failed: %v", err)
		}
	}

	fmt.Println("\n✅ Successfully connected to WhatsApp!")
	if client.Store.ID != nil {
		fmt.Printf("Logged in as: %s\n", client.Store.ID.User)
	} else {
		fmt.Println("Session active (Waiting for ID sync...)")
	}

	// 4. Input Loop for Target Selection
	go inputLoop()

	fmt.Println("\n--- MONITORING ACTIVE ---")
	fmt.Println("Commands:")
	fmt.Println("  'set <phone>' - Change the number to monitor (e.g., set 919876543210)")
	fmt.Println("  'all'        - Monitor all incoming messages")
	fmt.Println("  'exit'       - Close the application")
	fmt.Println("--------------------------")

	// Wait for interrupt
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	fmt.Println("\nShutting down...")
	client.Disconnect()
}

func inputLoop() {
	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Print("\n> ")
		if !scanner.Scan() {
			break
		}
		input := strings.TrimSpace(scanner.Text())
		
		if input == "exit" {
			os.Exit(0)
		} else if input == "all" {
			targetJIDMutex.Lock()
			targetJID = types.JID{}
			targetJIDMutex.Unlock()
			fmt.Println("Now monitoring ALL messages.")
		} else if strings.HasPrefix(input, "set ") {
			phone := strings.TrimSpace(strings.TrimPrefix(input, "set "))
			if phone == "" {
				fmt.Println("Error: Please provide a phone number.")
				continue
			}
			newJID := types.NewJID(phone, types.DefaultUserServer)
			targetJIDMutex.Lock()
			targetJID = newJID
			targetJIDMutex.Unlock()
			fmt.Printf("Target updated! Now monitoring: %s\n", newJID.String())
		} else {
			fmt.Println("Unknown command. Use 'set <phone>', 'all', or 'exit'.")
		}
	}
}

func eventHandler(evt interface{}) {
	switch v := evt.(type) {
	case *events.Message:
		sender := v.Info.Sender
		
		targetJIDMutex.RLock()
		tJID := targetJID
		targetJIDMutex.RUnlock()

		// Logic: 
		// 1. If we are monitoring ALL messages (tJID is empty), show EVERYTHING (including mine).
		// 2. If we are monitoring a SPECIFIC person, show only messages from them (ignore mine).
		isTarget := false
		if tJID.IsEmpty() {
			isTarget = true
		} else if sender.User == tJID.User {
			isTarget = true
		}

		if isTarget {
			messageText := extractText(v.Message)
			if messageText != "" {
				timestamp := time.Now().Format("15:04:05")
				
				// 1. Determine Identity Details
				displayName := sender.User // Fallback
				contact, _ := client.Store.Contacts.GetContact(context.Background(), sender)
				if contact.FullName != "" {
					displayName = contact.FullName
				} else if v.Info.PushName != "" {
					displayName = v.Info.PushName
				}

				resolvePhone := func(jid types.JID) string {
					if jid.Server == types.DefaultUserServer {
						return jid.User
					}
					
					// If it's a LID, try to find the PN mapping in the store
					if jid.Server == "lid" || jid.Server == types.HiddenUserServer {
						pnJID, err := client.Store.LIDs.GetPNForLID(context.Background(), jid)
						if err == nil && !pnJID.IsEmpty() {
							return pnJID.User
						}
					}
					
					return jid.User // Still LID if no mapping found
				}

				senderPhone := resolvePhone(sender)
				receiverPhone := resolvePhone(client.Store.GetJID())

				// Identify the conversation "Partner" (the other person in the chat)
				partnerPhone := senderPhone
				actualSenderName := displayName
				if v.Info.IsFromMe {
					senderPhone = resolvePhone(client.Store.GetJID())
					receiverPhone = resolvePhone(v.Info.Chat)
					partnerPhone = receiverPhone
					actualSenderName = "Me"
					if client.Store.PushName != "" {
						actualSenderName = client.Store.PushName
					}
				}
				
				// 3. Format Output
				logEntry := fmt.Sprintf("[%s] %s (%s): %s", timestamp, actualSenderName, senderPhone, messageText)
				output := fmt.Sprintf("%s - %s - %s - %s to %s : %s", 
					timestamp, 
					displayName, 
					sender.String(), 
					senderPhone, 
					receiverPhone, 
					messageText)
				
				fmt.Printf("\r%s\n> ", output)

				// 4. Store in Chat History
				historyMutex.Lock()
				chatHistory[partnerPhone] = append(chatHistory[partnerPhone], logEntry)
				currentHistory := make([]string, len(chatHistory[partnerPhone]))
				copy(currentHistory, chatHistory[partnerPhone])
				historyMutex.Unlock()

				// Send context to backend
				go sendToBackend(senderPhone, messageText, currentHistory)

				// 5. Triggers: Placed or Cancelled
				if v.Info.IsFromMe {
					if strings.Contains(messageText, "Your order has been placed!") {
						// Send history to invoice service directly
						go sendHistoryToInvoice(partnerPhone, displayName, currentHistory)
						
						fmt.Printf("\n[System] Order placed. Requesting PDF from makeaton for %s (%s)...\n", displayName, partnerPhone)
					} else if strings.Contains(messageText, "Order has been cancelled!") {
						// Silently clear history
						historyMutex.Lock()
						delete(chatHistory, partnerPhone)
						historyMutex.Unlock()
						fmt.Printf("\n[System] Chat history cleared for %s\n> ", partnerPhone)
					}
				}
			}
		}
	}
}

func extractText(msg *waE2E.Message) string {
	if msg == nil {
		return ""
	}
	if msg.Conversation != nil {
		return msg.GetConversation()
	}
	if msg.ExtendedTextMessage != nil {
		return msg.ExtendedTextMessage.GetText()
	}
	return ""
}

func sendToBackend(sender, message string, history []string) {
	backendURL := "https://invoice-makeaton-production.up.railway.app/api/messages"
	
	payload := map[string]interface{}{
		"sender":  sender,
		"message": message,
		"history": history,
	}
	
	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return
	}

	resp, err := http.Post(backendURL, "application/json", bytes.NewBuffer(jsonPayload))
	if err == nil {
		resp.Body.Close()
	}
}

func sendHistoryToInvoice(customerPhone string, customerName string, chats []string) {
	invoiceURL := "https://invoice-makeaton-production.up.railway.app/api/generate-invoice"
	
	// Prepare JSON payload
	requestBody, err := json.Marshal(map[string]interface{}{
		"chats":          chats,
		"customer_name":  customerName,
		"customer_phone": customerPhone,
	})
	if err != nil {
		fmt.Printf("\n[Error] Failed to marshal history: %v\n> ", err)
		return
	}

	resp, err := http.Post(invoiceURL, "application/json", bytes.NewBuffer(requestBody))
	if err != nil {
		fmt.Printf("\n[Error] Failed to connect to makeaton: %v\n> ", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		fmt.Printf("\n[System] Invoice request sent to makeaton for %s. Frontend will be notified.\n> ", customerName)
	} else {
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("\n[Error] Makeaton returned status %d: %s\n> ", resp.StatusCode, string(body))
	}
}

func saveBillingToFile(customerPhone string, data map[string]interface{}) {
	items, ok1 := data["items"].([]interface{})
	totals, ok2 := data["totals"].(map[string]interface{})

	if !ok1 || !ok2 {
		fmt.Printf("\n[Error] Invalid data format from backend\n> ")
		return
	}

	var builder strings.Builder
	builder.WriteString("==========================================\n")
	builder.WriteString("            BILLING INVOICE               \n")
	builder.WriteString("==========================================\n")
	builder.WriteString(fmt.Sprintf("Customer: %s\n", customerPhone))
	builder.WriteString(fmt.Sprintf("Date:     %s\n", time.Now().Format("2006-01-02 15:04:05")))
	builder.WriteString("------------------------------------------\n")
	builder.WriteString(fmt.Sprintf("%-20s %-5s %-10s\n", "Product", "Qty", "Price"))
	builder.WriteString("------------------------------------------\n")

	for _, itm := range items {
		item := itm.(map[string]interface{})
		builder.WriteString(fmt.Sprintf("%-20s %-5v %-10.2f\n", 
			item["item"], item["quantity"], item["price"]))
	}

	builder.WriteString("------------------------------------------\n")
	builder.WriteString(fmt.Sprintf("Subtotal: %10.2f\n", totals["subtotal"]))
	builder.WriteString(fmt.Sprintf("GST (%v%%): %10.2f\n", totals["gst_rate"], totals["gst"]))
	builder.WriteString("------------------------------------------\n")
	builder.WriteString(fmt.Sprintf("TOTAL:    %10.2f\n", totals["total"]))
	builder.WriteString("==========================================\n")

	filename := fmt.Sprintf("billing_%s.txt", customerPhone)
	err := os.WriteFile(filename, []byte(builder.String()), 0644)
	if err != nil {
		fmt.Printf("\n[Error] Failed to save billing file: %v\n> ", err)
	} else {
		fmt.Printf("\n[System] Billing file created: %s\n> ", filename)
	}
}
