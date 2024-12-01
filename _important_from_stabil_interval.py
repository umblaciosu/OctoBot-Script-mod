    last_pos_max = 0
    last_pos_min = 0
    ultimul_x = 0
    suma_varfuri_high = 0
    inc = 0
    line_max_exists = False
    line_min_exists = False
    procent_max = 0
    procent_min = 0

    for i in range(0, len(local_maxim)):
        for j in range (0,len(local_maxim)):

            # Cu cat % este diferenta intre maxime ?
            if ( local_maxim[i+j] != 0 ):
                procent_max = find_last(local_maxim,j) / local_maxim[i+j]
            if ( local_minim[i+j] != 0 ):
                procent_min = find_last(local_maxim,j) / local_minim[i+j]
            
            #if there is a much higher peak than the maximum peaks - no stability interval
            #if procent_max > 1 + proc_intre_vrf_line_IS and procent_max !=0:
            #    break

            #if there is a much lower peak than the minimum peaks - no stability interval
            #if procent_min < 1-proc_intre_vrf_line_IS and procent_min !=0:
            #    break
            
            #if abs(sb[i+j]) >= macd_max_delta:
            #    break
            
            if procent_max <= 1+proc_intre_vrf_line_IS and procent_max >= 1-proc_intre_vrf_line_IS:
                last_pos_max=i+j
            
            if procent_min <= 1+proc_intre_vrf_line_IS and procent_min >= 1-proc_intre_vrf_line_IS:
                last_pos_min=i+j

            # _____ verific daca exista alta linie de maxime intre varfuri _______
            #conditie pentru a face verificari doar dupa ce nr de bar-uri este suficient pentru a interoga indexul "interval_stabil"
            if len(line_max) >= interval_stabil:
                if line_max[i+j-1] != 0:
                    line_max_exists = True
            
            # _____ verific daca exista alta linie de minime intre varfuri ______
            if len(line_min) >= interval_stabil:
                if line_min[i+j-1] != 0:
                    line_min_exists = True
                
            ## ______ Definire interval stabilitate ______
            if last_pos_max !=0 and last_pos_max >=IS_length_min and line_max_exists == False:
                line_max.append(high[last_pos_max])
                #array.push(line_max,line.new(bar_index - last_pos_max-1, (high[last_pos_max] + high[1])/2, bar_index-1, (high[last_pos_max] + high[1])/2,color=color.green,width = 4))
                #log.info("Found max line with high[{1}] = {0}", high[last_pos_max], last_pos_max)
            else:
                #____ Verific daca am un interval mai mare de stabilitate ____
                if last_pos_max !=0 and last_pos_max >=IS_length_min and line_max_exists == True and abs(sb[j])-macd_max_delta <=0 and abs(sb[last_pos_max])<= macd_max_delta:
                    #log.iline_max = True
                    line_max.append(0)
                else:
                    line_max.append(0)
                    #array.push(line_max,na)
                    #log.info("pushed max_na")
            
            if last_pos_min !=0 and last_pos_min >=IS_length_min and line_min_exists == False:
                line_min.append(low[last_pos_min])
                #array.push(line_min,line.new(bar_index - last_pos_min-1, (low[last_pos_min] + low[1])/2, bar_index-1, (low[last_pos_min] + low[1])/2,color=color.red,width = 4))
                #log.info("Found min line with low[{1}] = {0}", low[last_pos_min], last_pos_min)
            else:
                if last_pos_min !=0 and last_pos_min >=IS_length_min and line_min_exists == True and abs(sb[j])-macd_max_delta <=0 and abs(sb[last_pos_min])<= macd_max_delta:
                    #log.info("sb = {0}, abs(sb)={1}", sb, abs(sb)-macd_max_delta)
                    #log.info("Found wider min line with low[{1}] = {0}", low[last_pos_min], last_pos_min)
                    wider_line_min = True
                    line_min.append(0)
                    #array.push(line_min,na)
                else:
                    line_min.append(0)
                    #array.push(line_min,na)
                    #log.info("pushed min_na")nfo("sb = {0}, abs(sb)={1}", sb, abs(sb)-macd_max_delta)
                    #log.info("Found wider max line with high[{1}] = {0}", high[last_pos_max], last_pos_max)
                    wider_